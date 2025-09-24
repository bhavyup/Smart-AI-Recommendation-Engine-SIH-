"""
Regional Language Support Module
Provides translation and localization capabilities for the AI Smart Allocation Engine
"""

import json
from typing import Dict, Any

class LanguageSupport:
    """Handles regional language support and translations"""
    
    def __init__(self):
        self.current_language = 'en'
        self.translations = self._load_translations()
        
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation files for different languages"""
        return {
            'en': {
                'app_title': 'AI Smart Allocation Engine',
                'app_subtitle': 'PM Internship Scheme - Find Your Perfect Internship Match',
                'candidate_info': 'Candidate Information',
                'full_name': 'Full Name',
                'education_level': 'Education Level',
                'skills': 'Skills',
                'skills_placeholder': 'e.g., Python, JavaScript, Data Analysis',
                'location': 'Preferred Location',
                'sector_interests': 'Sector Interests',
                'sector_placeholder': 'e.g., Technology, Finance, Healthcare',
                'social_category': 'Social Category',
                'prefers_rural': 'Prefer Rural Opportunities',
                'from_rural_area': 'From Rural Area',
                'first_generation': 'First Generation Graduate',
                'find_matches': 'Find My Internship Matches',
                'loading_text': 'AI is analyzing your profile and finding the best matches...',
                'recommendations_title': 'Your Top Internship Matches',
                'match_score': 'Match',
                'location_label': 'Location',
                'duration_label': 'Duration',
                'stipend_label': 'Stipend',
                'education_label': 'Education',
                'sector_label': 'Sector',
                'capacity_label': 'Capacity',
                'required_skills': 'Required Skills',
                'why_match': 'Why This Match?',
                'view_details': 'View Details',
                'apply_now': 'Apply Now',
                'rural_friendly': 'Rural Friendly',
                'diversity_focused': 'Diversity Focused',
                'strong_skill_alignment': 'Strong skill alignment',
                'good_skill_match': 'Good skill match',
                'perfect_location_match': 'Perfect location match',
                'good_location_fit': 'Good location fit',
                'education_matches': 'Education level matches',
                'sector_interests_match': 'Matches your sector interests',
                'diversity_support': 'Supports diversity and inclusion'
            },
            'hi': {
                'app_title': 'AI स्मार्ट आवंटन इंजन',
                'app_subtitle': 'पीएम इंटर्नशिप योजना - अपना सही इंटर्नशिप मैच खोजें',
                'candidate_info': 'उम्मीदवार की जानकारी',
                'full_name': 'पूरा नाम',
                'education_level': 'शिक्षा स्तर',
                'skills': 'कौशल',
                'skills_placeholder': 'जैसे, Python, JavaScript, Data Analysis',
                'location': 'पसंदीदा स्थान',
                'sector_interests': 'क्षेत्र रुचि',
                'sector_placeholder': 'जैसे, Technology, Finance, Healthcare',
                'social_category': 'सामाजिक श्रेणी',
                'prefers_rural': 'ग्रामीण अवसर पसंद करें',
                'from_rural_area': 'ग्रामीण क्षेत्र से',
                'first_generation': 'पहली पीढ़ी का स्नातक',
                'find_matches': 'मेरे इंटर्नशिप मैच खोजें',
                'loading_text': 'AI आपकी प्रोफ़ाइल का विश्लेषण कर रहा है और सबसे अच्छे मैच खोज रहा है...',
                'recommendations_title': 'आपके शीर्ष इंटर्नशिप मैच',
                'match_score': 'मैच',
                'location_label': 'स्थान',
                'duration_label': 'अवधि',
                'stipend_label': 'वजीफा',
                'education_label': 'शिक्षा',
                'sector_label': 'क्षेत्र',
                'capacity_label': 'क्षमता',
                'required_skills': 'आवश्यक कौशल',
                'why_match': 'यह मैच क्यों?',
                'view_details': 'विवरण देखें',
                'apply_now': 'अभी आवेदन करें',
                'rural_friendly': 'ग्रामीण अनुकूल',
                'diversity_focused': 'विविधता केंद्रित',
                'strong_skill_alignment': 'मजबूत कौशल संरेखण',
                'good_skill_match': 'अच्छा कौशल मैच',
                'perfect_location_match': 'सही स्थान मैच',
                'good_location_fit': 'अच्छा स्थान फिट',
                'education_matches': 'शिक्षा स्तर मैच',
                'sector_interests_match': 'आपकी क्षेत्र रुचि से मैच',
                'diversity_support': 'विविधता और समावेशन का समर्थन'
            },
            'ta': {
                'app_title': 'AI ஸ்மார்ட் ஒதுக்கீடு இயந்திரம்',
                'app_subtitle': 'பிஎம் பயிற்சி திட்டம் - உங்கள் சரியான பயிற்சி பொருத்தத்தைக் கண்டறியவும்',
                'candidate_info': 'விண்ணப்பதாரர் தகவல்',
                'full_name': 'முழு பெயர்',
                'education_level': 'கல்வி நிலை',
                'skills': 'திறன்கள்',
                'skills_placeholder': 'எ.கா., Python, JavaScript, Data Analysis',
                'location': 'விருப்பமான இடம்',
                'sector_interests': 'துறை ஆர்வங்கள்',
                'sector_placeholder': 'எ.கா., Technology, Finance, Healthcare',
                'social_category': 'சமூக வகை',
                'prefers_rural': 'கிராமிய வாய்ப்புகளை விரும்புகிறேன்',
                'from_rural_area': 'கிராமிய பகுதியிலிருந்து',
                'first_generation': 'முதல் தலைமுறை பட்டதாரி',
                'find_matches': 'எனது பயிற்சி பொருத்தங்களைக் கண்டறியவும்',
                'loading_text': 'AI உங்கள் சுயவிவரத்தை பகுப்பாய்வு செய்து சிறந்த பொருத்தங்களைக் கண்டறிகிறது...',
                'recommendations_title': 'உங்கள் முதன்மை பயிற்சி பொருத்தங்கள்',
                'match_score': 'பொருத்தம்',
                'location_label': 'இடம்',
                'duration_label': 'காலம்',
                'stipend_label': 'ஊதியம்',
                'education_label': 'கல்வி',
                'sector_label': 'துறை',
                'capacity_label': 'திறன்',
                'required_skills': 'தேவையான திறன்கள்',
                'why_match': 'இந்த பொருத்தம் ஏன்?',
                'view_details': 'விவரங்களைக் காண்க',
                'apply_now': 'இப்போது விண்ணப்பிக்கவும்',
                'rural_friendly': 'கிராமிய நட்பு',
                'diversity_focused': 'பன்முகத்தன்மை மையமாக',
                'strong_skill_alignment': 'வலுவான திறன் சீரமைப்பு',
                'good_skill_match': 'நல்ல திறன் பொருத்தம்',
                'perfect_location_match': 'சரியான இடம் பொருத்தம்',
                'good_location_fit': 'நல்ல இடம் பொருத்தம்',
                'education_matches': 'கல்வி நிலை பொருத்தம்',
                'sector_interests_match': 'உங்கள் துறை ஆர்வங்களுடன் பொருத்தம்',
                'diversity_support': 'பன்முகத்தன்மை மற்றும் உள்ளடக்கத்தை ஆதரிக்கிறது'
            }
        }
        
    def set_language(self, language_code: str):
        """Set the current language"""
        if language_code in self.translations:
            self.current_language = language_code
        else:
            print(f"Language {language_code} not supported. Using English.")
            self.current_language = 'en'
            
    def get_text(self, key: str) -> str:
        """Get translated text for a given key"""
        return self.translations.get(self.current_language, {}).get(key, key)
        
    def get_all_texts(self) -> Dict[str, str]:
        """Get all translated texts for current language"""
        return self.translations.get(self.current_language, {})
        
    def translate_candidate_data(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate candidate data labels"""
        translated = candidate_data.copy()
        
        # Translate education levels
        education_translations = {
            'en': {'Diploma': 'Diploma', 'Bachelor': 'Bachelor\'s Degree', 'Master': 'Master\'s Degree', 'PhD': 'PhD'},
            'hi': {'Diploma': 'डिप्लोमा', 'Bachelor': 'स्नातक', 'Master': 'स्नातकोत्तर', 'PhD': 'पीएचडी'},
            'ta': {'Diploma': 'டிப்ளோமா', 'Bachelor': 'இளங்கலை', 'Master': 'முதுகலை', 'PhD': 'முனைவர்'}
        }
        
        if 'education_level' in translated:
            translated['education_level'] = education_translations.get(
                self.current_language, 
                education_translations['en']
            ).get(translated['education_level'], translated['education_level'])
            
        return translated
        
    def translate_internship_data(self, internship_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate internship data"""
        translated = internship_data.copy()
        
        # Translate sectors
        sector_translations = {
            'en': {'Technology': 'Technology', 'Finance': 'Finance', 'Healthcare': 'Healthcare', 'Marketing': 'Marketing'},
            'hi': {'Technology': 'प्रौद्योगिकी', 'Finance': 'वित्त', 'Healthcare': 'स्वास्थ्य सेवा', 'Marketing': 'मार्केटिंग'},
            'ta': {'Technology': 'தொழில்நுட்பம்', 'Finance': 'நிதி', 'Healthcare': 'சுகாதாரம்', 'Marketing': 'விற்பனை'}
        }
        
        if 'sector' in translated:
            translated['sector'] = sector_translations.get(
                self.current_language,
                sector_translations['en']
            ).get(translated['sector'], translated['sector'])
            
        return translated
        
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {
            'en': 'English',
            'hi': 'हिन्दी',
            'ta': 'தமிழ்'
        }
        
    def format_currency(self, amount: int) -> str:
        """Format currency based on current language"""
        if self.current_language == 'hi':
            return f"₹{amount:,}"
        elif self.current_language == 'ta':
            return f"₹{amount:,}"
        else:
            return f"₹{amount:,}"
            
    def format_duration(self, months: int) -> str:
        """Format duration based on current language"""
        if self.current_language == 'hi':
            return f"{months} महीने"
        elif self.current_language == 'ta':
            return f"{months} மாதங்கள்"
        else:
            return f"{months} months"


