from transformers import AutoImageProcessor, RegNetForImageClassification
import torch
from datasets import load_dataset
import json
import os 
import PIL.Image as Image

# os.environ['CURL_CA_BUNDLE'] = ''

# dataset = load_dataset("huggingface/cats-image")
# image = dataset["test"]["image"][0]

input_path = "input/1.jpeg"
image = Image.open(input_path)

# image_processor = AutoImageProcessor.from_pretrained("facebook/regnet-y-040")
# model = RegNetForImageClassification.from_pretrained("facebook/regnet-y-040")

# # save the model to local
# model.save_pretrained("model/regnet-y-040-model")
# image_processor.save_pretrained("model/regnet-y-040-image-processor")

# load the model from local
image_processor = AutoImageProcessor.from_pretrained("model/regnet-y-040-image-processor")
model = RegNetForImageClassification.from_pretrained("model/regnet-y-040-model")

inputs = image_processor(image, return_tensors="pt")

with torch.no_grad():
    logits = model(**inputs).logits

# model predicts one of the 1000 ImageNet classes
predicted_label = logits.argmax(-1).item()
label_text = model.config.id2label[predicted_label-1]

print("Predicted class:", label_text)

with open("output/output.json", 'w', encoding="utf8") as f:
    json.dump({"label": label_text}, f, ensure_ascii=False)
