"""
Blendshape Controller - Converts audio/text to facial animations
Maps phonemes and emotions to VTuber blendshapes for realistic facial animation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class Blendshape:
    """Single blendshape frame"""
    timestamp: float  # Time in seconds
    shapes: Dict[str, float]  # Shape name -> value (0-1)
    emotion: str = "neutral"


class PhonemeMapper:
    """Maps phonemes to mouth blendshapes"""
    
    # Phoneme to blendshape mapping based on visemes
    PHONEME_MAP = {
        # Bilabial (lips together)
        'p': {'mouthClose': 0.8, 'mouthPucker': 0.3},
        'b': {'mouthClose': 0.8, 'mouthPucker': 0.3},
        'm': {'mouthClose': 0.9, 'mouthPucker': 0.2},
        
        # Labiodental (teeth on lip)
        'f': {'mouthOpen': 0.3, 'mouthLowerDownLeft': 0.2, 'mouthLowerDownRight': 0.2},
        'v': {'mouthOpen': 0.3, 'mouthLowerDownLeft': 0.2, 'mouthLowerDownRight': 0.2},
        
        # Dental/Alveolar
        't': {'mouthOpen': 0.2, 'tongueOut': 0.3},
        'd': {'mouthOpen': 0.2, 'tongueOut': 0.3},
        'n': {'mouthOpen': 0.15, 'tongueOut': 0.2},
        's': {'mouthOpen': 0.1, 'mouthSmile': 0.2},
        'z': {'mouthOpen': 0.1, 'mouthSmile': 0.2},
        'l': {'mouthOpen': 0.3, 'tongueOut': 0.4},
        
        # Velar
        'k': {'mouthOpen': 0.4, 'jawOpen': 0.3},
        'g': {'mouthOpen': 0.4, 'jawOpen': 0.3},
        
        # Vowels
        'a': {'mouthOpen': 0.7, 'jawOpen': 0.6},
        'e': {'mouthOpen': 0.4, 'mouthSmile': 0.3},
        'i': {'mouthOpen': 0.2, 'mouthSmile': 0.5},
        'o': {'mouthOpen': 0.5, 'mouthPucker': 0.6},
        'u': {'mouthOpen': 0.3, 'mouthPucker': 0.8},
        
        # Diphthongs
        'ai': {'mouthOpen': 0.5, 'mouthSmile': 0.4, 'jawOpen': 0.3},
        'ei': {'mouthOpen': 0.3, 'mouthSmile': 0.5},
        'oi': {'mouthOpen': 0.4, 'mouthPucker': 0.4},
        'au': {'mouthOpen': 0.6, 'mouthPucker': 0.5},
        
        # Silent/neutral
        'sil': {'mouthClose': 0.1, 'mouthOpen': 0.0},
        ' ': {'mouthClose': 0.1, 'mouthOpen': 0.0},
    }
    
    @classmethod
    def get_blendshape(cls, phoneme: str) -> Dict[str, float]:
        """Get blendshape values for a phoneme"""
        return cls.PHONEME_MAP.get(phoneme.lower(), cls.PHONEME_MAP['sil'])


class EmotionAnalyzer:
    """Analyzes text for emotional content"""
    
    EMOTION_KEYWORDS = {
        'happy': ['happy', 'joy', 'excited', 'great', 'awesome', 'amazing', 'wonderful', 'yay', '!'],
        'sad': ['sad', 'sorry', 'unfortunately', 'miss', 'lonely', 'depressed'],
        'angry': ['angry', 'mad', 'frustrated', 'annoyed', 'hate', 'terrible'],
        'surprised': ['wow', 'omg', 'surprised', 'shocked', 'unexpected', 'suddenly'],
        'love': ['love', 'heart', 'adore', 'dear', 'sweet', '❤️', '💕'],
        'thinking': ['hmm', 'think', 'maybe', 'perhaps', 'wonder', 'consider', '?'],
        'excited': ['excited', 'amazing', 'incredible', 'fantastic', 'woohoo', '!!!'],
        'neutral': []
    }
    
    EMOTION_BLENDSHAPES = {
        'happy': {
            'mouthSmile': 0.7,
            'eyeSquintLeft': 0.3,
            'eyeSquintRight': 0.3,
            'cheekPuff': 0.2
        },
        'sad': {
            'mouthFrownLeft': 0.5,
            'mouthFrownRight': 0.5,
            'browDownLeft': 0.4,
            'browDownRight': 0.4,
            'eyeWideLeft': -0.2,
            'eyeWideRight': -0.2
        },
        'angry': {
            'browDownLeft': 0.7,
            'browDownRight': 0.7,
            'eyeSquintLeft': 0.4,
            'eyeSquintRight': 0.4,
            'mouthFrownLeft': 0.3,
            'mouthFrownRight': 0.3,
            'noseSneerLeft': 0.2,
            'noseSneerRight': 0.2
        },
        'surprised': {
            'eyeWideLeft': 0.8,
            'eyeWideRight': 0.8,
            'browOuterUpLeft': 0.6,
            'browOuterUpRight': 0.6,
            'mouthOpen': 0.4,
            'jawOpen': 0.3
        },
        'love': {
            'mouthSmile': 0.6,
            'eyeSquintLeft': 0.4,
            'eyeSquintRight': 0.4,
            'cheekPuff': 0.3,
            'browInnerUp': 0.2
        },
        'thinking': {
            'browDownLeft': 0.2,
            'browOuterUpRight': 0.3,
            'eyeLookUp': 0.2,
            'mouthPucker': 0.1
        },
        'excited': {
            'mouthSmile': 0.9,
            'eyeWideLeft': 0.5,
            'eyeWideRight': 0.5,
            'browOuterUpLeft': 0.4,
            'browOuterUpRight': 0.4,
            'cheekPuff': 0.4
        },
        'neutral': {
            'mouthClose': 0.0,
            'browNeutral': 0.0
        }
    }
    
    def analyze(self, text: str) -> str:
        """Analyze text and return detected emotion"""
        
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        
        # Count keyword matches for each emotion
        emotion_scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        # Return emotion with highest score
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        # Check for exclamation marks (excitement)
        if '!' in text:
            return 'excited' if text.count('!') > 1 else 'happy'
        
        # Check for questions (thinking)
        if '?' in text:
            return 'thinking'
        
        return 'neutral'
    
    def get_emotion_blendshapes(self, emotion: str) -> Dict[str, float]:
        """Get blendshape values for an emotion"""
        return self.EMOTION_BLENDSHAPES.get(emotion, self.EMOTION_BLENDSHAPES['neutral'])


class BlendshapeController:
    """
    Main controller for generating blendshapes from audio/text
    """
    
    def __init__(self):
        self.phoneme_mapper = PhonemeMapper()
        self.emotion_analyzer = EmotionAnalyzer()
        self.current_emotion = "neutral"
        self.blend_speed = 0.1  # Smoothing factor
    
    async def generate_from_audio(
        self,
        audio_data: bytes,
        sample_rate: int,
        text: Optional[str] = None
    ) -> List[Blendshape]:
        """
        Generate blendshapes from audio data
        Uses phoneme detection and amplitude analysis
        """
        
        # Convert audio bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Analyze emotion from text if provided
        emotion = self.emotion_analyzer.analyze(text) if text else "neutral"
        self.current_emotion = emotion
        
        # Generate blendshapes based on audio amplitude and timing
        blendshapes = await self._process_audio_to_blendshapes(
            audio_array,
            sample_rate,
            emotion
        )
        
        return blendshapes
    
    async def _process_audio_to_blendshapes(
        self,
        audio_array: np.ndarray,
        sample_rate: int,
        emotion: str
    ) -> List[Blendshape]:
        """Process audio array into blendshape frames"""
        
        blendshapes = []
        
        # Frame size for blendshape updates (30 FPS)
        frame_duration = 1.0 / 30.0  # 33ms per frame
        frame_size = int(sample_rate * frame_duration)
        
        # Get base emotion blendshapes
        emotion_shapes = self.emotion_analyzer.get_emotion_blendshapes(emotion)
        
        # Process audio in frames
        for i in range(0, len(audio_array), frame_size):
            frame = audio_array[i:i+frame_size]
            
            if len(frame) == 0:
                break
            
            # Calculate amplitude for mouth opening
            amplitude = np.abs(frame).mean()
            
            # Generate mouth shapes based on amplitude
            mouth_shapes = self._generate_mouth_from_amplitude(amplitude)
            
            # Combine emotion and mouth shapes
            combined_shapes = {**emotion_shapes}
            for key, value in mouth_shapes.items():
                if key in combined_shapes:
                    # Blend values
                    combined_shapes[key] = (combined_shapes[key] + value) / 2
                else:
                    combined_shapes[key] = value
            
            # Create blendshape frame
            timestamp = i / sample_rate
            blendshapes.append(Blendshape(
                timestamp=timestamp,
                shapes=combined_shapes,
                emotion=emotion
            ))
        
        return blendshapes
    
    def _generate_mouth_from_amplitude(self, amplitude: float) -> Dict[str, float]:
        """Generate mouth blendshapes based on audio amplitude"""
        
        # Map amplitude to mouth opening (0-1 range)
        mouth_open = min(1.0, amplitude * 3.0)  # Scale amplitude
        
        # Create realistic mouth movement
        shapes = {}
        
        if mouth_open > 0.7:
            # Wide open (loud speech)
            shapes['mouthOpen'] = mouth_open
            shapes['jawOpen'] = mouth_open * 0.7
            shapes['mouthWide'] = mouth_open * 0.3
        elif mouth_open > 0.3:
            # Medium open (normal speech)
            shapes['mouthOpen'] = mouth_open
            shapes['jawOpen'] = mouth_open * 0.5
        elif mouth_open > 0.1:
            # Slightly open (quiet speech)
            shapes['mouthOpen'] = mouth_open
            shapes['jawOpen'] = mouth_open * 0.3
        else:
            # Closed (silence)
            shapes['mouthClose'] = 0.1
        
        return shapes
    
    async def generate_from_text(self, text: str) -> List[Blendshape]:
        """
        Generate blendshapes from text only (without audio)
        Used for quick responses or text-based animations
        """
        
        # Analyze emotion
        emotion = self.emotion_analyzer.analyze(text)
        emotion_shapes = self.emotion_analyzer.get_emotion_blendshapes(emotion)
        
        # Estimate duration based on text length (rough approximation)
        # Average speaking rate: 150 words per minute
        words = len(text.split())
        duration = (words / 150) * 60  # Convert to seconds
        
        # Generate simple talking animation
        blendshapes = []
        frame_count = int(duration * 30)  # 30 FPS
        
        for i in range(frame_count):
            timestamp = i / 30.0
            
            # Simple sine wave for mouth movement
            t = timestamp * 10  # Frequency
            mouth_open = abs(np.sin(t)) * 0.5
            
            shapes = {**emotion_shapes}
            shapes['mouthOpen'] = mouth_open
            shapes['jawOpen'] = mouth_open * 0.5
            
            blendshapes.append(Blendshape(
                timestamp=timestamp,
                shapes=shapes,
                emotion=emotion
            ))
        
        return blendshapes
    
    def interpolate_blendshapes(
        self,
        from_shapes: Dict[str, float],
        to_shapes: Dict[str, float],
        factor: float
    ) -> Dict[str, float]:
        """Smoothly interpolate between two blendshape states"""
        
        result = {}
        all_keys = set(from_shapes.keys()) | set(to_shapes.keys())
        
        for key in all_keys:
            from_val = from_shapes.get(key, 0.0)
            to_val = to_shapes.get(key, 0.0)
            result[key] = from_val + (to_val - from_val) * factor
        
        return result
    
    def to_tcp_commands(self, blendshape: Blendshape) -> List[str]:
        """Convert blendshape to TCP commands for neurosync_s1"""
        
        commands = []
        
        # Set emotion face
        if blendshape.emotion != "neutral":
            commands.append(f"FACE.{blendshape.emotion.capitalize()}")
        
        # Set individual blendshapes (if supported)
        for shape_name, value in blendshape.shapes.items():
            if value > 0.1:  # Only send significant values
                # Convert to morph target command
                commands.append(f"MT_{shape_name}_{value:.2f}")
        
        return commands


class LipSyncGenerator:
    """
    Advanced lip sync generation using phoneme detection
    """
    
    def __init__(self):
        self.phoneme_mapper = PhonemeMapper()
    
    async def generate_from_phonemes(
        self,
        phonemes: List[Tuple[str, float]],  # List of (phoneme, duration)
        emotion: str = "neutral"
    ) -> List[Blendshape]:
        """Generate blendshapes from phoneme sequence"""
        
        blendshapes = []
        current_time = 0.0
        
        emotion_shapes = EmotionAnalyzer().get_emotion_blendshapes(emotion)
        
        for phoneme, duration in phonemes:
            # Get blendshape for this phoneme
            mouth_shapes = self.phoneme_mapper.get_blendshape(phoneme)
            
            # Combine with emotion
            combined = {**emotion_shapes, **mouth_shapes}
            
            # Create frames for this phoneme duration
            frame_count = int(duration * 30)  # 30 FPS
            for i in range(frame_count):
                timestamp = current_time + (i / 30.0)
                
                # Add some variation to make it more natural
                variation = 1.0 + np.sin(timestamp * 20) * 0.1
                
                varied_shapes = {
                    k: v * variation for k, v in combined.items()
                }
                
                blendshapes.append(Blendshape(
                    timestamp=timestamp,
                    shapes=varied_shapes,
                    emotion=emotion
                ))
            
            current_time += duration
        
        return blendshapes