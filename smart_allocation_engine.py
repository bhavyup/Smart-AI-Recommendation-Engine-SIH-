import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import joblib
from typing import List, Dict, Any
import json

class SmartAllocationEngine:
    """
    AI-based Smart Allocation Engine for PM Internship Scheme
    Matches candidates with internship opportunities using ML algorithms
    """
    
    def __init__(self):
        self.candidate_data = []
        self.internship_data = []
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.scaler = StandardScaler()
        self.model_trained = False
        
    def load_sample_data(self):
        """Load sample internship and candidate data"""
        
        # Sample internship data
        self.internship_data = [
            {
                'id': 1,
                'title': 'Software Development Intern',
                'company': 'TechCorp India',
                'sector': 'Technology',
                'location': 'Bangalore',
                'skills_required': ['Python', 'JavaScript', 'React', 'SQL'],
                'education_level': 'Bachelor',
                'capacity': 5,
                'duration_months': 6,
                'stipend': 15000,
                'rural_friendly': True,
                'diversity_focused': True
            },
            {
                'id': 2,
                'title': 'Data Science Intern',
                'company': 'DataAnalytics Ltd',
                'sector': 'Technology',
                'location': 'Mumbai',
                'skills_required': ['Python', 'Machine Learning', 'Statistics', 'Pandas'],
                'education_level': 'Master',
                'capacity': 3,
                'duration_months': 4,
                'stipend': 20000,
                'rural_friendly': False,
                'diversity_focused': True
            },
            {
                'id': 3,
                'title': 'Marketing Intern',
                'company': 'BrandBuilders',
                'sector': 'Marketing',
                'location': 'Delhi',
                'skills_required': ['Digital Marketing', 'Social Media', 'Content Writing', 'Analytics'],
                'education_level': 'Bachelor',
                'capacity': 4,
                'duration_months': 3,
                'stipend': 12000,
                'rural_friendly': True,
                'diversity_focused': False
            },
            {
                'id': 4,
                'title': 'Finance Intern',
                'company': 'FinTech Solutions',
                'sector': 'Finance',
                'location': 'Chennai',
                'skills_required': ['Excel', 'Financial Analysis', 'Accounting', 'PowerBI'],
                'education_level': 'Bachelor',
                'capacity': 2,
                'duration_months': 5,
                'stipend': 18000,
                'rural_friendly': False,
                'diversity_focused': True
            },
            {
                'id': 5,
                'title': 'Healthcare Research Intern',
                'company': 'MedResearch Institute',
                'sector': 'Healthcare',
                'location': 'Hyderabad',
                'skills_required': ['Research', 'Data Analysis', 'Medical Knowledge', 'Python'],
                'education_level': 'Master',
                'capacity': 3,
                'duration_months': 6,
                'stipend': 16000,
                'rural_friendly': True,
                'diversity_focused': True
            }
        ]
        
        print(f"Loaded {len(self.internship_data)} sample internships")
        
    def add_candidate(self, candidate_info: Dict[str, Any]):
        """Add a new candidate to the system"""
        candidate_id = len(self.candidate_data) + 1
        candidate_info['id'] = candidate_id
        self.candidate_data.append(candidate_info)
        return candidate_id
        
    def calculate_skill_match_score(self, candidate_skills: List[str], 
                                  internship_skills: List[str]) -> float:
        """Calculate skill matching score between candidate and internship"""
        if not candidate_skills or not internship_skills:
            return 0.0
            
        candidate_skills_lower = [skill.lower() for skill in candidate_skills]
        internship_skills_lower = [skill.lower() for skill in internship_skills]
        
        matches = sum(1 for skill in internship_skills_lower 
                     if skill in candidate_skills_lower)
        
        return matches / len(internship_skills_lower)
        
    def calculate_location_preference_score(self, candidate_location: str, 
                                         internship_location: str,
                                         candidate_prefers_rural: bool,
                                         internship_rural_friendly: bool) -> float:
        """Calculate location preference score"""
        if candidate_location.lower() == internship_location.lower():
            return 1.0
            
        # Bonus for rural-friendly internships if candidate prefers rural
        if candidate_prefers_rural and internship_rural_friendly:
            return 0.8
            
        # Same state/region bonus (simplified)
        return 0.6
        
    def calculate_diversity_score(self, candidate_info: Dict[str, Any], 
                               internship_info: Dict[str, Any]) -> float:
        """Calculate diversity and affirmative action score"""
        score = 0.0
        
        # Check if internship is diversity-focused
        if internship_info.get('diversity_focused', False):
            score += 0.3
            
        # Check candidate's background for affirmative action
        if candidate_info.get('from_rural_area', False):
            score += 0.2
            
        if candidate_info.get('social_category') in ['SC', 'ST', 'OBC']:
            score += 0.2
            
        if candidate_info.get('first_generation_graduate', False):
            score += 0.1
            
        return min(score, 1.0)
        
    def calculate_education_match_score(self, candidate_education: str, 
                                     internship_education: str) -> float:
        """Calculate education level matching score"""
        education_levels = {
            'Diploma': 1,
            'Bachelor': 2,
            'Master': 3,
            'PhD': 4
        }
        
        candidate_level = education_levels.get(candidate_education, 2)
        internship_level = education_levels.get(internship_education, 2)
        
        # Exact match gets highest score
        if candidate_level == internship_level:
            return 1.0
            
        # Candidate with higher education gets good score
        if candidate_level > internship_level:
            return 0.8
            
        # Candidate with lower education gets lower score
        return 0.4
        
    def calculate_sector_interest_score(self, candidate_interests: List[str], 
                                      internship_sector: str) -> float:
        """Calculate sector interest matching score"""
        if not candidate_interests:
            return 0.5  # Neutral score if no interests specified
            
        if internship_sector.lower() in [interest.lower() for interest in candidate_interests]:
            return 1.0
            
        return 0.3
        
    def get_recommendations(self, candidate_info: Dict[str, Any], 
                          top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top internship recommendations for a candidate"""
        
        if not self.internship_data:
            self.load_sample_data()
            
        recommendations = []
        
        for internship in self.internship_data:
            # Calculate various matching scores
            skill_score = self.calculate_skill_match_score(
                candidate_info.get('skills', []),
                internship['skills_required']
            )
            
            location_score = self.calculate_location_preference_score(
                candidate_info.get('location', ''),
                internship['location'],
                candidate_info.get('prefers_rural', False),
                internship['rural_friendly']
            )
            
            education_score = self.calculate_education_match_score(
                candidate_info.get('education_level', 'Bachelor'),
                internship['education_level']
            )
            
            sector_score = self.calculate_sector_interest_score(
                candidate_info.get('sector_interests', []),
                internship['sector']
            )
            
            diversity_score = self.calculate_diversity_score(
                candidate_info,
                internship
            )
            
            # Calculate weighted overall score
            weights = {
                'skill': 0.3,
                'location': 0.2,
                'education': 0.2,
                'sector': 0.15,
                'diversity': 0.15
            }
            
            overall_score = (
                skill_score * weights['skill'] +
                location_score * weights['location'] +
                education_score * weights['education'] +
                sector_score * weights['sector'] +
                diversity_score * weights['diversity']
            )
            
            recommendation = {
                'internship': internship,
                'scores': {
                    'overall': round(overall_score, 3),
                    'skill_match': round(skill_score, 3),
                    'location_match': round(location_score, 3),
                    'education_match': round(education_score, 3),
                    'sector_match': round(sector_score, 3),
                    'diversity_bonus': round(diversity_score, 3)
                },
                'match_reasons': self._generate_match_reasons(
                    skill_score, location_score, education_score, 
                    sector_score, diversity_score
                )
            }
            
            recommendations.append(recommendation)
            
        # Sort by overall score and return top N
        recommendations.sort(key=lambda x: x['scores']['overall'], reverse=True)
        return recommendations[:top_n]
        
    def _generate_match_reasons(self, skill_score: float, location_score: float,
                              education_score: float, sector_score: float,
                              diversity_score: float) -> List[str]:
        """Generate human-readable reasons for the match"""
        reasons = []
        
        if skill_score > 0.7:
            reasons.append("Strong skill alignment")
        elif skill_score > 0.4:
            reasons.append("Good skill match")
            
        if location_score > 0.8:
            reasons.append("Perfect location match")
        elif location_score > 0.6:
            reasons.append("Good location fit")
            
        if education_score > 0.8:
            reasons.append("Education level matches")
            
        if sector_score > 0.8:
            reasons.append("Matches your sector interests")
            
        if diversity_score > 0.3:
            reasons.append("Supports diversity and inclusion")
            
        return reasons
        
    def save_model(self, filepath: str):
        """Save the trained model"""
        model_data = {
            'candidate_data': self.candidate_data,
            'internship_data': self.internship_data,
            'model_trained': self.model_trained
        }
        joblib.dump(model_data, filepath)
        
    def load_model(self, filepath: str):
        """Load a saved model"""
        model_data = joblib.load(filepath)
        self.candidate_data = model_data['candidate_data']
        self.internship_data = model_data['internship_data']
        self.model_trained = model_data['model_trained']


