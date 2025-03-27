import gradio as gr
from openai import OpenAI
import requests
import json
import os
import time

class TravelPlanner:
    def __init__(self, api_key):
        try:
            if not api_key or not api_key.startswith('sk-'):
                raise ValueError("Geçersiz API anahtarı formatı")
            
            self.client = OpenAI(api_key=api_key)
            self.assistant_id = ("OPENAI_ASSISTANT_ID")
            
            try:
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "Test"}],
                    max_tokens=1
                )
            except Exception as api_error:
                raise ValueError(f"API anahtarı doğrulanamadı: {str(api_error)}")
                
        except Exception as e:
            print(f"API initialization error: {e}")
            raise Exception("API anahtarı geçersiz veya bir hata oluştu. Lütfen geçerli bir API anahtarı giriniz.")

    def get_weather(self, city):
        try:
            encoded_city = requests.utils.quote(city)
            url = f"https://wttr.in/{encoded_city}?format=3"
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.text.strip()
                return {
                    'description': weather_data,
                    'temperature': weather_data.split()[1] if len(weather_data.split()) > 1 else 'N/A',
                    'humidity': 'N/A'
                }
        except Exception as e:
            print(f"Weather API error: {e}")
        return {'description': 'Hava durumu bilgisi alınamadı', 'temperature': 'N/A', 'humidity': 'N/A'}

    def get_coordinates(self, destination):
        try:
            encoded_destination = requests.utils.quote(destination)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_destination}&format=json"
            headers = {
                'User-Agent': 'TravelPlanner/1.0',
                'Accept-Language': 'tr'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        'lat': float(data[0]['lat']),
                        'lon': float(data[0]['lon'])
                    }
        except Exception as e:
            print(f"Geocoding API error: {e}")
        return None

    def get_places(self, location, place_type):
        overpass_url = "https://overpass-api.de/api/interpreter"
        radius = 5000
        
        osm_tags = {
            "museum": "tourism=museum",
            "tourist_attraction": "tourism=attraction",
            "park": "leisure=park",
            "natural_feature": "natural=*",
            "night_club": "amenity=nightclub",
            "restaurant": "amenity=restaurant",
            "hospital": "amenity=hospital",
            "clinic": "amenity=clinic",
            "place_of_worship": "amenity=place_of_worship",
            "conference_centre": "amenity=conference_centre",
            "shopping_mall": "shop=mall",
            "cafe": "amenity=cafe",
            "sports_centre": "leisure=sports_centre",
            "stadium": "leisure=stadium",
            "fitness_centre": "leisure=fitness_centre",
        }
        
        tag = osm_tags.get(place_type, "tourism=attraction")
        
        query = f"""
        [out:json][timeout:25];
        (
          node[{tag}](around:{radius},{location['lat']},{location['lon']});
          way[{tag}](around:{radius},{location['lat']},{location['lon']});
          relation[{tag}](around:{radius},{location['lat']},{location['lon']});
        );
        out center;
        """
        
        response = requests.post(overpass_url, data={"data": query})
        if response.status_code == 200:
            data = response.json()
            results = []
            for element in data.get('elements', [])[:3]:  # Limit to 3 results
                name = element.get('tags', {}).get('name', 'Unnamed Place')
                results.append({'name': name})
            return results
        return []

    def get_ai_recommendations(self, destination, interests, weather, price_range=None):
        prompt = f"""As a travel expert, provide personalized recommendations for {destination}.
        Interests: {', '.join(interests)}
        Current weather: {weather['description']}
        {f'Budget: {price_range}' if price_range else ''}
        
        Please suggest activities and tips based on these interests and weather conditions.
        Keep the response concise and friendly in Turkish language."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable travel advisor who provides personalized travel recommendations in Turkish."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "AI önerileri şu anda kullanılamıyor."

    def chat_with_assistant(self, message):
        try:
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful travel assistant who provides information in Turkish."},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
                    
        except Exception as e:
            print(f"Chat API error: {e}")
            return "Üzgünüm, şu anda yanıt veremiyorum."

    def plan_trip(self, user_id, destination, price_range, interests):
        location = self.get_coordinates(destination)
        if not location:
            return "Hedef konum bulunamadı"
        
        weather = self.get_weather(destination)
        
        response = f"{destination} için Seyahat Planı\n\n"
        response += f"Bütçe: {price_range}\n"
        response += f"Hava Durumu: {weather['description']}\n\n"

        
        prompt = f"""As a travel expert, provide personalized recommendations for {destination}.
        Budget: {price_range}
        Interests: {', '.join(interests)}
        Current weather: {weather['description']}
        
        Please suggest activities and tips based on these interests, budget, and weather conditions.
        Include budget-friendly recommendations that match the specified price range.
        Keep the response concise and friendly in Turkish language."""

        ai_suggestions = self.get_ai_recommendations(destination, interests, weather, price_range)
        response += f"AI Önerileri:\n{ai_suggestions}\n\n"

        for interest in interests:
            places = []
            interest = interest.lower()
            
            if interest == "kültürel":
                places = self.get_places(location, "museum") + self.get_places(location, "tourist_attraction")
                response += "Kültürel Mekanlar:\n"
            elif interest == "doğal":
                places = self.get_places(location, "park") + self.get_places(location, "natural_feature")
                response += "Doğal Güzellikler:\n"
            elif interest == "eğlence":
                places = self.get_places(location, "night_club") + self.get_places(location, "restaurant")
                response += "Eğlence Mekanları:\n"
            elif interest == "sağlık":
                places = self.get_places(location, "hospital") + self.get_places(location, "clinic")
                response += "Sağlık Merkezleri:\n"
            elif interest == "gastronomi":
                places = self.get_places(location, "restaurant") + self.get_places(location, "cafe")
                response += "Gastronomi Mekanları:\n"
            elif interest == "inanç":
                places = self.get_places(location, "place_of_worship")
                response += "İnanç Mekanları:\n"
            elif interest == "kongre":
                places = self.get_places(location, "conference_centre")
                response += "Kongre Merkezleri:\n"
            elif interest == "moda":
                places = self.get_places(location, "shopping_mall")
                response += "Alışveriş Merkezleri:\n"
            elif interest == "spor":
                places = (self.get_places(location, "sports_centre") + 
                         self.get_places(location, "stadium") +
                         self.get_places(location, "fitness_centre"))
                response += "Spor Tesisleri:\n"
            else:
                continue

            if places:  
                for place in places[:3]:
                    response += f"- {place['name']}\n"
                response += "\n"
                time.sleep(1)

        return response

def create_interface():
    planner = None
    
    def plan_trip_interface(api_key, destination, price_range, interests):
        nonlocal planner
        try:
            if not api_key:
                return "Lütfen OpenAI API anahtarınızı giriniz."
            
            if not api_key.startswith('sk-'):
                return "Geçersiz API anahtarı formatı. API anahtarı 'sk-' ile başlamalıdır."
            
            if planner is None or planner.client.api_key != api_key:
                try:
                    planner = TravelPlanner(api_key)
                except Exception as e:
                    return str(e)
            
            if not interests:
                return "Lütfen en az bir ilgi alanı seçiniz."
            
            if not destination:
                return "Lütfen gidilecek yeri giriniz."
            
            return planner.plan_trip("default_user", destination, price_range, interests)
            
        except Exception as e:
            print(f"Plan creation error: {e}")
            return "Seyahat planı oluşturulurken bir hata oluştu. Lütfen API anahtarınızı kontrol edin."

    def respond(message, history):
        nonlocal planner
        if not planner:
            return "", [{"role": "user", "content": message}, 
                      {"role": "assistant", "content": "Lütfen önce API anahtarınızı girin."}]
        try:
            bot_message = planner.chat_with_assistant(message)
            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": bot_message}
            ]
            return "", history
        except Exception as e:
            print(f"Chat error: {e}")
            return "", history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."}
            ]

    def clear_chat():
        return [], []

    with gr.Blocks(
            theme='hmb/amethyst',
            css="""
                .gradio-container {
                    background: linear-gradient(rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.5)), url('https://images.pexels.com/photos/1482927/pexels-photo-1482927.jpeg');
                    background-size: cover;
                    background-position: center;
                    background-attachment: fixed;
                }
                .custom-button {
                    background-color: #9B59B6 !important;
                    border: 1px solid #8E44AD !important;
                }
                .custom-button:hover {
                    background-color: #8E44AD !important;
                }
                h1, h3 {
                    text-align: center !important;
                    font-weight: bold !important;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.2) !important;
                }
                h1 {
                    font-size: 2.5em !important;
                }
                h3 {
                    font-size: 1.5em !important;
                }
            """
        ) as interface:
            gr.Markdown(
                """
                # 🌍 Seyahat Planlayıcı
                ### Tercihlerinize göre özelleştirilmiş seyahat planları oluşturun!
                """
            )
        
            with gr.Row():
                with gr.Column():
                    api_key_input = gr.Textbox(
                        label="OpenAI API Key",
                        placeholder="sk-...",
                        type="password",
                        value="",
                        scale=1
                    )
                    
                    destination = gr.Textbox(
                        label="Gidilecek Yer",
                        placeholder="Şehir veya ülke adı girin...",
                        scale=1
                    )
                    
                    price_range = gr.Radio(
                        choices=["Ekonomik (0-10000 TL)", "Orta (10000-20000 TL)", "Lüks (30000+ TL)"],
                        label="Bütçe Aralığı",
                        value="Orta (10000-20000 TL)",
                        scale=1
                    )
                    
                    with gr.Accordion("🎯 İlgi Alanları", open=False):
                        interests = gr.CheckboxGroup(
                            choices=[
                                "Kültürel", "Doğal", "Eğlence",
                                "Sağlık", "Gastronomi", "İnanç",
                                "Kongre", "Moda", "Spor"  
                            ],
                            label="İlgi Alanlarınız",
                            info="Birden fazla seçim yapabilirsiniz",
                            value=[],
                            scale=1,
                            interactive=True
                        )
                    
                    submit_btn = gr.Button(
                        "🎯 Seyahat Planı Oluştur",
                        variant="primary",
                        scale=1,
                        elem_classes="custom-button"
                    )

                with gr.Column():
                    output = gr.Textbox(
                        label="Seyahat Planınız",
                        lines=10,
                        scale=1
                    )

       
            with gr.Accordion("💬 Seyahat Asistanı ile Sohbet", open=False):
                chatbot = gr.Chatbot(height=300, type="messages")
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Mesajınız",
                        placeholder="Seyahat ile ilgili sorularınızı buraya yazın...",
                        show_label=True,
                        scale=4
                    )
                
                with gr.Row():
                    submit_btn_chat = gr.Button("Gönder", scale=2)
                    clear = gr.Button("🗑️ Sohbeti Temizle", scale=1)

                
                msg.submit(fn=respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
                submit_btn_chat.click(fn=respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
                clear.click(fn=clear_chat, outputs=[msg, chatbot])

        
            gr.Markdown("""
            <style>
            .custom-button {
                background-color: #9B59B6 !important;
                border: 1px solid #8E44AD !important;
            }
            .custom-button:hover {
                background-color: #8E44AD !important;
            }
            </style>
        """)

            submit_btn.click(
            fn=plan_trip_interface,
            inputs=[api_key_input, destination, price_range, interests],  
            outputs=output
        )

            return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)