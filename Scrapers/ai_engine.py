import logging
import time
import io
import requests
import base64
import os
from PIL import Image
from Scrapers.config import MAX_AI_CALLS

logger = logging.getLogger(__name__)

class GroqProptechAI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("API_KEY") or os.getenv("GROQ_API_KEY")
        self.ai_calls_made = 0

        if self.api_key:
            self.text_model = "llama-3.3-70b-versatile"
            self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        else:
            self.api_key = None
            logger.warning("⚠️ API_KEY not found. AI Analysis will be skipped.")

    def reset_counter(self):
        """Resets the daily/batch call counter."""
        self.ai_calls_made = 0

    def analyze_description(self, description, category="Apartment - Sale"):
        """Sends property description to Groq and returns a 5-point investment report based on category."""
        if not self.api_key:
            return "AI Analysis unavailable."

        if self.ai_calls_made >= MAX_AI_CALLS:
            logger.warning(f"⚠️ AI Skip: Limit ({MAX_AI_CALLS}) reached for this batch. Saving API costs.")
            return "AI skipped (Batch Limit Reached to save costs)."

        try:
            time.sleep(1)

            if "Rent" in category:
                prompt = f"""
        You are a Warsaw Real Estate Expert. Analyze this {category} description:
        1. CONDITION: (Ready to move in, Needs cleaning, or Needs work?)
        2. RENTAL DEMAND: (High, Med, or Low for this area/type?)
        3. TARGET TENANT: (Students, Professionals, Families, or Business?)
        4. INVESTMENT STRATEGY: (Long-term rent, Short-term/Airbnb?)
        5. URGENCY: (Motivated landlord? Open to price negotiation?)

        Provide 5 short bullet points in English.
        Description: {description[:3500]}
        """
            elif "Commercial" in category:
                prompt = f"""
        You are a Warsaw Commercial Real Estate Expert. Analyze this {category} description:
        1. CONDITION: (Ready to use, White box, or Needs adaptation?)
        2. BUSINESS POTENTIAL: (High, Med, or Low? What type of business fits best?)
        3. LOCATION/TRAFFIC: (Mentions high foot traffic, visibility, or parking?)
        4. ROI STRATEGY: (Good for leasing out or owner-operator?)
        5. URGENCY: (Motivated seller/landlord? Open to negotiation?)

        Provide 5 short bullet points in English.
        Description: {description[:3500]}
        """
            else:
                prompt = f"""
        You are a Warsaw Real Estate Investment Expert. Analyze this Polish description:
        1. CONDITION: (Renovated, New, or Needs Work?)
        2. FLIP POTENTIAL: (High, Med, or Low?)
        3. MARKET SPEED: (Estimate: <7 days, 2 weeks, or 1+ month?)
        4. INVESTMENT STRATEGY: (Buy-to-let or Quick Flip?)
        5. URGENCY: (Motivated seller? Mentions quick sale, leaving country, or open to negotiation?)

        Provide 5 short bullet points in English.
        Description: {description[:3500]}
        """
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.text_model,
                "messages": [{"role": "user", "content": prompt}]
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            text = response.json()['choices'][0]['message']['content'].strip()

            if text:
                self.ai_calls_made += 1
                return text

            return "AI summary unavailable."

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "AI Analysis failed."

    def analyze_with_vision(self, description, image_urls, category="Apartment - Sale", sqm=0):
        """
        Sends description AND property photos to Groq Vision.
        """
        if not self.api_key:
            return "AI Analysis unavailable."

        if self.ai_calls_made >= MAX_AI_CALLS:
            return "AI skipped (Batch Limit Reached)."

        images_to_analyze = []

        if image_urls:
            try:
                response = requests.get(image_urls[0], timeout=5)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    img.thumbnail((512, 512))
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=75)

                    base64_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    img_data_url = f"data:image/jpeg;base64,{base64_img}"
                    images_to_analyze.append(img_data_url)
            except Exception as e:
                logger.error(f"❌ Image compression error: {e}")

        try:
            time.sleep(1)

            if "Rent" in category:
                prompt = f"""
            You are a Warsaw Real Estate Expert. Analyze photos and description.
            1. VISUAL CONDITION: (Modern, PRL/Old, or Fresh?)
            2. REFRESH ESTIMATE: (Approx cost to make it tenant-ready in PLN)
            3. RENTAL APPEAL: (Who will rent this?)
            
            Description: {description[:3500]}
            """
            elif "Commercial" in category:
                prompt = f"""
            You are a Warsaw Commercial Expert. Analyze photos for adaptation needs.
            1. SPACE READINESS: (White box, needs floors/ceilings, or ready?)
            2. ADAPTATION COST: (Estimate renovation for business use)
            3. POTENTIAL: (Office, Retail, or Gastro?)
            
            Description: {description[:3500]}
            """
            else:
                prompt = f"""
            You are an elite Warsaw Real Estate Investment Analyst and Master Negotiator.
            Analyze the provided photo and READ THE ENTIRE DESCRIPTION carefully for an investment project ({sqm} m2). 
            
            MARKET RATES (Warsaw 2026):
            - Cosmetic Refresh: 1,800 PLN/m2
            - Standard Reno (Bath/Kitchen): 3,000 PLN/m2
            - Total Gut Renovation: 4,500+ PLN/m2
            
            CRITICAL INSTRUCTIONS:
            1. VISUAL & STRUCTURAL STATUS: Assess the real condition. Is it modernized, 90s style, or a disaster?
            2. SMART RENO BUDGET: Calculate based on ACTUAL condition and {sqm}m2. If the description explicitly states it is newly renovated, high standard, or ready to move in, state the renovation budget as 0 PLN (or a minimal cosmetic budget). DO NOT calculate a full gut renovation for a new apartment.
            3. MASTER NEGOTIATION LEVER (EXTREME DETAIL REQUIRED): Read the description meticulously. Even if the apartment is "newly renovated" or "perfect", you MUST find every single disadvantage or hidden cost mentioned or implied. Look for flaws such as: ground floor (parter), 4th floor without elevator (brak windy), mandatory extra fees for parking/storage (dodatkowo płatne), loud street, old building (wielka płyta), high monthly HOA fees (wysoki czynsz), poor layout, or specific legal status issues. List exactly how these specific flaws can be aggressively used to justify a massive price drop during negotiations with the seller.
            4. NO FAKE PRICES: DO NOT invent or assume a market price or target purchase price. Focus purely on the renovation cost and the specific percentage/value discounts justified by the flaws found in the text.

            Provide a highly detailed, professional report in English using punchy bullet points. Be specific with PLN amounts and strategic negotiation arguments. Do not cut your sentences short.
            Description: {description[:3500]}
            """

            content_parts = [{"type": "text", "text": prompt}]
            for img_data in images_to_analyze:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": img_data}
                })

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.vision_model,
                "messages": [{"role": "user", "content": content_parts}],
                "max_tokens": 1200,
                "temperature": 0.3
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=25)

            if response.status_code != 200:
                error_details = response.text[:200]
                logger.error(f"Groq API Error: {error_details}")
                return f"⚠️ Groq API Rejected the request. Reason: {error_details}"

            response.raise_for_status()
            text = response.json()['choices'][0]['message']['content'].strip()

            if text:
                self.ai_calls_made += 1
                return text

            return "AI visual summary unavailable."

        except Exception as e:
            logger.error(f"AI Vision Error: {e}")
            return f"AI Vision Analysis failed: {str(e)[:100]}"