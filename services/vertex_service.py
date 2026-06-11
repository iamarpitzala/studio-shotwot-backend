import os
import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part

def get_vertex_client():
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION", "asia-south1")
    vertexai.init(project=project_id, location=region)

def optimize_prompt_with_gemini(brief: str) -> str:
    """
    Optimizes a user brief into a dense prompt using Gemini 1.5 Pro.
    """
    get_vertex_client()
    optimizer = GenerativeModel("gemini-1.5-pro")
    
    optimization_instruction = f"""
    You are a professional prompt engineer for an AI image generation system 
    serving Indian B2B businesses.
    
    Convert this user brief into a detailed image generation prompt.
    
    User brief: "{brief}"
    
    Your optimized prompt must include:
    - Specific lighting description (direction, quality, temperature)
    - Camera angle and perspective
    - Background environment with specific India-relevant details
    - Color palette and mood
    - Composition and framing
    - Photographic style (e.g. professional corporate photography, 85mm lens)
    
    Keep it under 200 words. Return ONLY the prompt. No explanation.
    No preamble. No labels.
    """
    
    response = optimizer.generate_content(optimization_instruction)
    return response.text.strip()

def generate_image_with_gemini_2_5(optimized_prompt: str, reference_image_bytes: bytes, aspect_ratio: str) -> bytes:
    """
    Generates an image with Gemini 2.5 Flash image generation utilizing a reference image.
    """
    get_vertex_client()
    # Using the exact preview tag recommended in guidelines/instructions:
    generator = GenerativeModel("gemini-2.5-flash-preview-05-20")
    
    reference_part = Part.from_data(
        data=base64.b64encode(reference_image_bytes).decode("utf-8"),
        mime_type="image/jpeg"
    )
    
    generation_prompt = f"""
    Generate a professional marketing image based on this description:
    
    {optimized_prompt}
    
    The reference image provided shows the subject (person, logo, or object) 
    that must appear in the generated image.
    
    Non-negotiable constraints:
    - Preserve the subject from the reference image with 100% identity fidelity
    - Face features, skin tone, and physical appearance must be identical to reference
    - The subject should be naturally integrated into the described scene
    - Lighting on the subject must match the scene's light source
    - Final output must look like a real professional photograph
    - Aspect ratio: {aspect_ratio}
    - No text overlays, no watermarks, no borders
    """
    
    response = generator.generate_content([
        generation_prompt,
        "Reference subject (preserve exactly):",
        reference_part
    ])
    
    output_part = response.candidates[0].content.parts[0]
    
    if not hasattr(output_part, 'inline_data') or not output_part.inline_data:
        if hasattr(output_part, 'text') and output_part.text:
            raise ValueError(f"Gemini did not return an image. Response: {output_part.text}")
        raise ValueError("Gemini did not return an image. Response was text only.")
        
    return base64.b64decode(output_part.inline_data.data)
