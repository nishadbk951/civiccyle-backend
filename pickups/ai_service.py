import json
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from google.genai import types
from django.conf import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)


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


def analyze_waste_image(image_file):
    
    try:
        
        optimized_bytes = _prepare_ai_thumbnail(image_file)

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

        image_file.seek(0)

        result = json.loads(response.text)
        return result

    except Exception as e:
        image_file.seek(0)
        error_str = str(e)
        print(f"Gemini AI Service Error: {error_str}")

        if "503" in error_str or "UNAVAILABLE" in error_str:
            user_msg = "AI server is currently experiencing high traffic. Please wait 5 seconds and try again."
        elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            user_msg = "AI request limit reached temporarily. Please wait 30 seconds and try again."
        else:
            user_msg = "Unable to analyze the image right now. Please try again."

        return {
            "is_valid": False,
            "detected_item": "Manual Check Required",
            "error_message": user_msg
        }