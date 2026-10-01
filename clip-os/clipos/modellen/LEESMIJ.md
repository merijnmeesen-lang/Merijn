# Modellen

- `face_detection_yunet_2023mar.onnx`: YuNet-gezichtsdetector uit [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
  (MIT-licentie). SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
  Wordt gebruikt door `clipos/reframe.py` via `cv2.FaceDetectorYN`; ontbreekt het bestand, dan valt Clip-OS terug op de
  eenvoudigere Haar-detector die in OpenCV zit.
