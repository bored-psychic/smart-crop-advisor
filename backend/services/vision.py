import numpy as np
from PIL import Image
from typing import Dict, Any, Optional
from core.models import ModelManager
from core.constants import DISEASE_META

# Maps PlantVillage class names + HSV fallback labels → DISEASE_META keys
_CLASS_TO_META = {
    'Apple___Apple_scab':                                  'apple scab',
    'Apple___Black_rot':                                   'apple black rot',
    'Apple___Cedar_apple_rust':                            'apple cedar rust',
    'Apple___healthy':                                     'healthy',
    'Blueberry___healthy':                                 'healthy',
    'Cherry___healthy':                                    'healthy',
    'Cherry___Powdery_mildew':                             'cherry powdery mildew',
    'Corn___Cercospora_leaf_spot Gray_leaf_spot':          'corn cercospora leaf spot',
    'Corn___Common_rust':                                  'corn common rust',
    'Corn___healthy':                                      'healthy',
    'Corn___Northern_Leaf_Blight':                         'corn northern leaf blight',
    'Grape___Black_rot':                                   'grape black rot',
    'Grape___Esca_(Black_Measles)':                        'grape esca',
    'Grape___healthy':                                     'healthy',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)':          'grape leaf blight',
    'Orange___Haunglongbing_(Citrus_greening)':            'default',
    'Peach___Bacterial_spot':                              'peach bacterial spot',
    'Peach___healthy':                                     'healthy',
    'Pepper,_bell___Bacterial_spot':                       'pepper bell bacterial spot',
    'Pepper,_bell___healthy':                              'healthy',
    'Potato___Early_blight':                               'potato early blight',
    'Potato___healthy':                                    'healthy',
    'Potato___Late_blight':                                'potato late blight',
    'Raspberry___healthy':                                 'healthy',
    'Soybean___healthy':                                   'healthy',
    'Squash___Powdery_mildew':                             'squash powdery mildew',
    'Strawberry___healthy':                                'healthy',
    'Strawberry___Leaf_scorch':                            'strawberry leaf scorch',
    'Tomato___Bacterial_spot':                             'tomato bacterial spot',
    'Tomato___Early_blight':                               'tomato early blight',
    'Tomato___healthy':                                    'healthy',
    'Tomato___Late_blight':                                'tomato late blight',
    'Tomato___Leaf_Mold':                                  'tomato leaf mold',
    'Tomato___Septoria_leaf_spot':                         'tomato septoria leaf spot',
    'Tomato___Spider_mites Two-spotted_spider_mite':       'tomato spider mites',
    'Tomato___Target_Spot':                                'tomato target spot',
    'Tomato___Tomato_mosaic_virus':                        'tomato mosaic virus',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus':              'tomato yellow leaf curl virus',
    # HSV fallback labels
    'Healthy Plant':               'healthy',
    'Late Blight / Stem Rot':      'tomato late blight',
    'Early Blight (Alternaria)':   'tomato early blight',
    'Leaf Curl Virus':             'tomato yellow leaf curl virus',
    'Possible Fungal Infection':   'default',
}

_SEVERITY_COLOR = {'High': 'red', 'Medium': 'orange', 'Low': 'green', 'None': 'green'}


def _display_name(class_name: str) -> str:
    """Tomato___Early_blight → Tomato Early Blight"""
    return class_name.replace('___', ' ').replace('_', ' ').replace(',', '').title()


class VisionService:
    @staticmethod
    async def _claude_diagnose(image_bytes: bytes, crop: str) -> Optional[Dict[str, Any]]:
        try:
            import base64, json
            from anthropic import AsyncAnthropic
            from core.config import settings
            if not settings.ANTHROPIC_API_KEY:
                return None
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            img_b64 = base64.standard_b64encode(image_bytes).decode()
            resp = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=[{
                    "type": "text",
                    "text": (
                        "You are a plant pathologist diagnosing crop diseases, nutrient deficiencies, "
                        "and pest damage from photos. Be specific and accurate.\n\n"
                        "Respond ONLY with valid JSON, no markdown fences:\n"
                        '{"disease":"Full disease or condition name","severity":"High|Medium|Low|None",'
                        '"confidence":82,"color":"red|orange|green",'
                        '"treatment":"specific treatment with product name and dose",'
                        '"prevention":"how to prevent recurrence",'
                        '"action":"single most urgent action right now",'
                        '"top3":[["Condition1",82],["Condition2",12],["Condition3",6]],'
                        '"model_used":"Claude Vision API"}'
                    ),
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64},
                        },
                        {
                            "type": "text",
                            "text": f"Diagnose this {crop} plant image. JSON only.",
                        },
                    ],
                }],
            )
            return json.loads(resp.content[0].text)
        except Exception:
            return None

    @staticmethod
    async def analyze_image_pixels(img: Image.Image, image_bytes: bytes = b"", crop_type: str = "Unknown") -> Dict[str, Any]:
        # Try Claude Vision first
        if image_bytes:
            claude_result = await VisionService._claude_diagnose(image_bytes, crop_type)
            if claude_result:
                return claude_result

        model_obj, class_names = ModelManager.load_vision_model()

        if model_obj is not None and class_names is not None:
            try:
                is_tflite = hasattr(model_obj, 'get_input_details')
                if is_tflite:
                    inp_details = model_obj.get_input_details()
                    out_details = model_obj.get_output_details()
                    inp_shape   = inp_details[0]['shape']
                    h, w        = int(inp_shape[1]), int(inp_shape[2])
                    img_resized = img.convert('RGB').resize((w, h))
                    img_array   = np.array(img_resized, dtype=np.float32) / 255.0
                    img_batch   = np.expand_dims(img_array, axis=0)
                    model_obj.set_tensor(inp_details[0]['index'], img_batch)
                    model_obj.invoke()
                    preds = model_obj.get_tensor(out_details[0]['index'])[0]
                else:
                    inp_shape   = model_obj.input_shape
                    h, w        = int(inp_shape[1]), int(inp_shape[2])
                    img_resized = img.convert('RGB').resize((w, h))
                    img_array   = np.array(img_resized, dtype=np.float32) / 255.0
                    img_batch   = np.expand_dims(img_array, axis=0)
                    preds       = model_obj.predict(img_batch, verbose=0)[0]

                top3_idx   = np.argsort(preds)[::-1][:3]
                top_idx    = int(top3_idx[0])
                confidence = int(round(float(preds[top_idx]) * 100))
                class_name = class_names[top_idx]
                top3       = [(class_names[i], int(round(float(preds[i]) * 100))) for i in top3_idx]
                return VisionService._format_result(class_name, confidence, "Deep Learning Model (TFLite)", top3)
            except Exception:
                pass

        return VisionService._hsv_analysis(img)

    @staticmethod
    def _hsv_analysis(img: Image.Image) -> Dict[str, Any]:
        img_rgb = img.convert('RGB').resize((200, 150))
        arr     = np.array(img_rgb) / 255.0

        r, g, b   = arr[..., 0], arr[..., 1], arr[..., 2]
        max_val   = np.max(arr, axis=-1)
        min_val   = np.min(arr, axis=-1)
        delta     = max_val - min_val
        v         = max_val
        s         = np.zeros_like(max_val)
        np.divide(delta, max_val, out=s, where=max_val != 0)

        h        = np.zeros_like(max_val)
        mask_r   = (max_val == r) & (delta != 0)
        mask_g   = (max_val == g) & (delta != 0)
        mask_b   = (max_val == b) & (delta != 0)
        h[mask_r] = (g[mask_r] - b[mask_r]) / delta[mask_r] % 6
        h[mask_g] = (b[mask_g] - r[mask_g]) / delta[mask_g] + 2
        h[mask_b] = (r[mask_b] - g[mask_b]) / delta[mask_b] + 4
        h *= 60

        total         = h.size
        healthy_green = ((h >= 80) & (h <= 160) & (s > 0.25) & (v > 0.2) & (v < 0.85)).sum()
        yellow        = ((h >= 40) & (h <= 75)  & (s > 0.35) & (v > 0.45)).sum()
        brown         = ((h >= 10) & (h <= 42)  & (s > 0.28) & (v < 0.65)).sum()

        br, yr, gr = brown / total, yellow / total, healthy_green / total

        if gr > 0.52 and br < 0.06 and yr < 0.06:
            label, conf = 'Healthy Plant',             min(97, int(78 + gr * 25))
        elif br > 0.13:
            label, conf = 'Late Blight / Stem Rot',    min(92, int(70 + br * 55))
        elif br > 0.07:
            label, conf = 'Early Blight (Alternaria)',  min(89, int(65 + br * 52))
        elif yr > 0.16:
            label, conf = 'Leaf Curl Virus',            min(85, int(62 + yr * 38))
        else:
            label, conf = 'Possible Fungal Infection',  58

        return VisionService._format_result(label, conf, "HSV Pixel Analysis (Fallback)", [])

    @staticmethod
    def _format_result(class_name: str, confidence: int, model_label: str, top3: list) -> Dict[str, Any]:
        meta_key = _CLASS_TO_META.get(class_name, 'default')
        meta     = DISEASE_META.get(meta_key, DISEASE_META['default'])
        severity = meta.get('severity', 'Medium')

        display = _display_name(class_name) if '___' in class_name else class_name

        return {
            "disease":    display,
            "confidence": confidence,
            "severity":   severity,
            "color":      _SEVERITY_COLOR.get(severity, 'orange'),
            "treatment":  meta.get('treatment',  DISEASE_META['default']['treatment']),
            "prevention": meta.get('prevention', DISEASE_META['default']['prevention']),
            "action":     meta.get('action',     DISEASE_META['default']['action']),
            "top3":       top3,
            "model_used": model_label,
        }
