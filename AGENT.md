Build a local Python tool.

Goal:
Scan a folder of Nikon .NEF RAW files, find files where:
1. there is a bird in the image
2. the bird is in focus

Then create a subfolder named selected_birds_in_focus and copy matched .NEF files into it.

Rules:
- Use Python
- Do not move or modify original files
- Support recursive scanning
- Use a pretrained bird/object detection model
- Judge sharpness mainly on the detected bird region
- Provide a CLI, requirements.txt, and README
- First make an MVP that can run locally