import json
import os
import time
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from google.genai import types
from django.conf import settings


def _get_api_keys():
    keys = []
    primary = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')
    backup = os.getenv('GEMINI_API_KEY_BACKUP')
    if primary:
        keys.append(primary)
    if backup:
        keys.append(backup)
    return keys


def _prepare_ai_thumbnail(image_file):
    image_file.seek(0)
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)

    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')

    img.thumbnail((512, 512), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=70, optimize=True)
    image_file.seek(0)  # Reset file pointer to 0 for subsequent AWS S3 upload
    return buffer.getvalue()


def _parse_json_response(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def analyze_waste_image(image_file):
    api_keys = _get_api_keys()
    if not api_keys:
        return {
            "is_valid": False,
            "detected_item": "",
            "error_message": "AI service is not configured. Please contact support."
        }

    try:
        optimized_bytes = _prepare_ai_thumbnail(image_file)
    except Exception as e:
        print(f"Image Processing Error: {e}")
        return {
            "is_valid": False,
            "detected_item": "",
            "error_message": "Invalid or corrupted image file. Please retake the photo."
        }

    prompt = """You are a strict quality-control AI for a dry-waste recycling company.
Analyze the uploaded image and evaluate the items visible in it.

ACCEPTED CATEGORIES (You MUST classify valid items into ONLY ONE of these exact 7 uppercase category labels):
- PLASTIC (bottles, containers, hard plastics, clean plastic packaging)
- METAL (iron, steel, aluminium cans, copper, wires, tin)
- PAPER (newspapers, cardboard boxes, books, office paper)
- E_WASTE (electronic devices, cables, chargers, appliances, batteries)
- FURNITURE (old wooden sofas, chairs, tables, cupboards, wood items)
- GLASS (glass bottles, jars)
- TEXTILE (old clothes, fabrics, bags)

STRICT EVALUATION RULES:
- Case 1 (Pure Accepted Items): If ALL visible waste items belong to the 7 accepted categories above, set "is_valid" to true. If multiple accepted categories are present in the same photo, pick the single DOMINANT category by volume.
- Case 2 (Contaminated / Mixed with Rejected Items): If the image contains accepted items MIXED with non-accepted items (such as food waste, organic/wet waste, diapers, medical waste, soil, or construction debris), set "is_valid" to false and explain that mixed wet/non-recyclable waste is not allowed.
- Case 3 (Fully Rejected / Non-Waste): If the image contains ONLY non-accepted items (like food waste, garden leaves, selfies, animals, empty rooms, or blurry/unclear objects), set "is_valid" to false.

CRITICAL OUTPUT CONSTRAINT:
- When "is_valid" is true, "detected_item" MUST be strictly one of these exact 7 strings: "PLASTIC", "METAL", "PAPER", "E_WASTE", "FURNITURE", "GLASS", or "TEXTILE". Do NOT add adjectives, extra words, or punctuation.
- When "is_valid" is false, "detected_item" MUST be an empty string "".

Return ONLY a valid JSON object with these exact 3 keys:
{
    "is_valid": true or false,
    "detected_item": "PLASTIC",
    "error_message": ""
}
"""

    max_retries = 3
    retry_delays = [2, 4]
    last_error_str = ""

    for attempt in range(max_retries):
        
        key_index = attempt % len(api_keys)
        client = genai.Client(api_key=api_keys[key_index])

        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[
                    types.Part.from_bytes(data=optimized_bytes, mime_type='image/jpeg'),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )

            try:
                image_file.seek(0)
            except Exception:
                pass

            return _parse_json_response(response.text)

        except Exception as e:
            last_error_str = str(e)
            print(f"Gemini AI Service Error (Attempt {attempt + 1}/{max_retries}): {last_error_str}")

            is_retryable = any(
                code in last_error_str
                for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
            )

            if is_retryable and attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            break

    try:
        image_file.seek(0)
    except Exception:
        pass

    if "503" in last_error_str or "UNAVAILABLE" in last_error_str:
        user_msg = "AI server is currently experiencing high traffic. Please wait 5 seconds and try again."
    elif "429" in last_error_str or "RESOURCE_EXHAUSTED" in last_error_str:
        user_msg = "AI request limit reached temporarily. Please wait 30 seconds and try again."
    else:
        user_msg = "Unable to analyze the image right now. Please try again."

    return {
        "is_valid": False,
        "detected_item": "",
        "error_message": user_msg
    }