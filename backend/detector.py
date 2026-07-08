import os
import sys
import json
import argparse

class MediaAIDetector:
    """
    Core AI Media Detector class for integration into other Python applications.
    Utilizes a pre-trained Vision Transformer (ViT) to analyze images and video frames.
    """
    def __init__(self, model_name="capcheck/ai-image-detection", threshold=0.5):
        try:
            import numpy as np
            import cv2
            from PIL import Image
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "Missing AI Detector dependencies. Please run: pip install transformers torch opencv-python pillow"
            )
        self.model_name = model_name

        self.threshold = threshold
        self._pipeline = None

    @property
    def pipeline(self):
        # Lazy loading so model isn't loaded unless detection is actually triggered
        if self._pipeline is None:
            from transformers import pipeline
            self._pipeline = pipeline("image-classification", model=self.model_name)
        return self._pipeline

    def detect_image(self, image_path):
        """
        Analyzes an image file.
        Returns:
            is_ai (bool): True if the image is detected as AI-generated.
            fake_score (float): Probability score of the image being synthetic/fake.
        """
        from PIL import Image
        try:
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            raise ValueError(f"Could not open image file: {e}")

        results = self.pipeline(image)
        fake_score = 0.0
        for res in results:
            if res['label'].upper() == 'FAKE':
                fake_score = res['score']
                break

        is_ai = fake_score >= self.threshold
        return is_ai, fake_score

    def detect_video(self, video_path, sample_frames=20):
        """
        Analyzes a video file by sampling frames.
        Returns:
            is_ai (bool): True if average score meets the threshold.
            avg_score (float): Average AI confidence score across sampled frames.
            frame_details (list): Timestamps and scores for each sampled frame.
        """
        import cv2
        from PIL import Image
        import numpy as np
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        sample_interval = max(1, frame_count // sample_frames)

        predictions = []
        timestamps = []

        curr_frame = 0
        processed_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if curr_frame % sample_interval == 0 and processed_count < sample_frames:
                # Convert BGR frame to RGB PIL Image
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)

                # Inference
                results = self.pipeline(pil_img)
                fake_score = 0.0
                for res in results:
                    if res['label'].upper() == 'FAKE':
                        fake_score = res['score']
                        break

                predictions.append(fake_score)
                timestamp = curr_frame / fps if fps > 0 else (curr_frame / 10.0)
                timestamps.append(round(timestamp, 2))
                processed_count += 1

            curr_frame += 1

        cap.release()

        if not predictions:
            return False, 0.0, []

        avg_score = float(np.mean(predictions))
        is_ai = avg_score >= self.threshold

        frame_details = [
            {"time_seconds": t, "ai_confidence": float(score)} 
            for t, score in zip(timestamps, predictions)
        ]

        return is_ai, avg_score, frame_details

    def detect(self, file_path, sample_frames=20):
        """
        Inspects a file, routes it to the correct handler, and returns a structured dictionary.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target file does not exist: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff']
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

        if ext in image_exts:
            is_ai, score = self.detect_image(file_path)
            return {
                "file_path": os.path.abspath(file_path),
                "media_type": "image",
                "is_ai": is_ai,
                "ai_confidence": score
            }
        elif ext in video_exts:
            is_ai, score, timeline = self.detect_video(file_path, sample_frames)
            return {
                "file_path": os.path.abspath(file_path),
                "media_type": "video",
                "is_ai": is_ai,
                "ai_confidence": score,
                "temporal_analysis": timeline
            }
        else:
            # Fallback: Attempt image classification
            try:
                is_ai, score = self.detect_image(file_path)
                return {
                    "file_path": os.path.abspath(file_path),
                    "media_type": "image (fallback)",
                    "is_ai": is_ai,
                    "ai_confidence": score
                }
            except Exception:
                raise ValueError(f"Unsupported file format: '{ext}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AURA CLI - AI Media Auditor")
    parser.add_argument("file", help="Path to the image or video file to audit")
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=0.5, 
        help="Sensitivity threshold (0.1 to 0.9, default: 0.5)"
    )
    parser.add_argument(
        "--samples", 
        type=int, 
        default=20, 
        help="Number of frames to sample for video files (default: 20)"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Format output results as JSON for scripting pipelines"
    )

    args = parser.parse_args()
    
    # Initialize detector
    detector = MediaAIDetector(threshold=args.threshold)

    try:
        results = detector.detect(args.file, sample_frames=args.samples)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("=" * 60)
            print("🛡️ AURA AI MEDIA AUDIT REPORT")
            print("=" * 60)
            print(f"Target:        {results['file_path']}")
            print(f"Format:        {results['media_type'].upper()}")
            print(f"Audit:         {'⚠️  AI GENERATED DETECTED' if results['is_ai'] else '✅  AUTHENTIC HUMAN CONTENT'}")
            print(f"Confidence:    {results['ai_confidence']:.2%}")
            print("=" * 60)
            
            if results['media_type'] == 'video' and results['temporal_analysis']:
                print(f"Sampled {len(results['temporal_analysis'])} frames across timeline.")
                high_conf = max(f['ai_confidence'] for f in results['temporal_analysis'])
                print(f"Peak AI frame confidence: {high_conf:.2%}")
                
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
