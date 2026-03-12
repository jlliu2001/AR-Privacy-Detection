import sys
import requests
import cv2
import numpy as np
import pandas as pd
import glob
from datetime import datetime


from flask import Flask, request, jsonify
import tempfile
import os
import subprocess
import json
from openai import OpenAI
from openai import AzureOpenAI
import openai

import time
import base64
import json
from concurrent.futures import ThreadPoolExecutor



def check_privacy(image_path, vlm_mode="gpt-4o-mini"):
    print("check_privacy")
    if vlm_mode=="gpt-4o-mini":
        vlm_model = GPTAzure("gpt-4o-mini")
    elif vlm_mode=="gpt-4o":
        vlm_model = GPTAzure("gpt-4o")
    elif vlm_mode=="llava4":
        vlm_model = LLaVA()
    print('VLM model loaded!')

    try:

        result=vlm_model.query(image_path=image_path)

        result_json = json.loads(result)
 
    except Exception as e:
        print('Error:', str(e))
        os.remove(image_path)
        return result_json

    return result_json

class GPTAzure():
    def __init__(self, name):
        print('GPTAzureFT is in use.\n')
        self.set_API_key()
        self.deployment_name = name
        self.temperature = 0.0
        print(f'self.deployment_name = {self.deployment_name}')
    
    def set_API_key(self):

        self.client = AzureOpenAI(
            api_key=os.environ.get("AZURE_API_KEY"),
            api_version=os.environ.get("AZURE_API_VERSION"),
            azure_endpoint=os.environ.get("AZURE_ENDPOINT")
        )
    

    
    def query(self, image_path=None, try_num=0, icl_num=0):

        msg="Please analyze whether this image contains any personal or sensitive information."
        try:
            if image_path:
                return self.__do_query_with_image(msg, image_path, icl_num)
            else:
                return self.__do_query(msg, icl_num)
        except openai.BadRequestError:
            return json.dumps({"privacy": False, "error": "BadRequestError"})
        except openai.RateLimitError:
            print(f"RateLimitError, waiting for 10 seconds...")
            time.sleep(10)
            return self.query(msg, image_path, try_num+1, icl_num)
    
    def __do_query(self, msg, icl_num=0):
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": "You are a privacy and security detection assistant. The user will upload an image. Please determine whether the image contains sensitive personal information such as ID cards, bank cards, passports, driver's licenses, social security cards, phone numbers, addresses, or email addresses. If it does, reply True, otherwise reply False. Only reply True or False."},
                {"role": "user", "content": msg}
            ],
            temperature=self.temperature
        )
        response = completion.choices[0].message.content
        # print(f'Response: {response}\n')
        return response
    
    def __do_query_with_image(self,msg, image_path, icl_num=0):
        """
        Query with both text and image input
        Args:
            msg (str): Text message
            image_path (str): Path to the image file
            icl_num (int): Optional, in-context learning parameter
        Returns:
            str: JSON response with privacy detection result
        """
        
        try:
            # Read and encode the image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            if image_b64 is not None:
                print('image success.')
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an assistant for privacy risk detection in AR images. The input is an image where any detected text has been blurred, so you cannot directly read the exact words. Instead, follow a three-step reasoning process: 1. Scene Description: Briefly describe the environment and objects in the image to understand the context. (e.g., livingroom, office desk, computer screen, handwritten notes, etc.)2. Text Topic Inference: For each blurred text region, infer the most likely topic or type of information based on its position, surrounding objects, and overall scene context. For example, blurred text on a plastic card might be an ID card, on a sticky note it might be a phone number, on a computer screen it could be an email or resume.3. Privacy Risk Assessment: Determine if the inferred text is likely to contain sensitive personal or financial information. The following categories should be considered privacy risks:(1)Identity documents (ID cards, student cards, passports, etc.)(2)Handwritten notes with phone numbers, emails, home addresses, or passwords(3)Digital screens (computer/phone) showing messages, forms, resumes, transcripts, etc.(4)Financial objects (bank cards, passbooks, etc.) Only reply True or False for the user's question."},
                    {"role": "user", "content": [
                        {"type": "text", "text": msg},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],


                temperature=self.temperature

            )
            response = completion.choices[0].message.content
            print('response:',response)
            # Process response like gpt4o_image_check.py
            try:
                reply = response.strip().lower()
                is_privacy = "true" in reply
            except Exception as e:
                is_privacy = False
            return json.dumps({"privacy": is_privacy})
        # except Exception as e:
        except openai.APIConnectionError as e:
            print(f"API connection error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except openai.RateLimitError as e:
            print(f"RateLimitError: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
                
        except openai.APIError as e:
            print(f"API error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
            
        except Exception as e:
            print(f"unknown error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})


    def do_query_with_image_description(self, msg, image_path, icl_num=0):
        """
        Query with both text and image input
        Args:
            msg (str): Text message
            image_path (str): Path to the image file
            icl_num (int): Optional, in-context learning parameter
        Returns:
            str: JSON response with privacy detection result
        """
        
        try:
            # Read and encode the image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            if image_b64 is not None:
                print('image success.')
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a privacy and security detection assistant. The user will upload an image with blurring for security protection. Please determine whether the image contains sensitive personal information, mainly contain 4 types:[1]Identity Documents(ID cards, passports, driver's licenses, student cards),[2]Financial Information(Bank cards, credit cards, bank statements),[3]Information in hand-write note(Notes with phone numbers, address information, printed emails,Password notes),[4]Personal Documents on computer/phone(tables, research paper/report, transcripts, excel within data).I hope you can follow the steps to analyze:Describe the whole scene--infer what topics about the text information--Does the current context make any information sensitive--give me the answer. If it does, reply True, otherwise reply False. Only reply True or False."},
                    {"role": "user", "content": [
                        {"type": "text", "text": msg},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],

                
                temperature=self.temperature

            )
            response = completion.choices[0].message.content
            print('response:',response)
            # Process response like gpt4o_image_check.py
            try:
                reply = response.strip().lower()
                is_privacy = "true" in reply
            except Exception as e:
                is_privacy = False
            return json.dumps({"privacy": is_privacy})
        # except Exception as e:
        except openai.APIConnectionError as e:
            print(f"API connection error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except openai.RateLimitError as e:
            print(f"RateLimitError: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
                
        except openai.APIError as e:
            print(f"API error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
            
        except Exception as e:
            print(f"unknown error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})

    def describe_image(self, image_path):
        """
        Generate a text description of the image using VLM
        Args:
            image_path (str): Path to the image file
        Returns:
            str: Text description of the image
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an image description assistant. Please provide a detailed description of what you see in the image, including any text, objects, documents, or personal information visible."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Please describe this image in detail."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],
                temperature=self.temperature
            )
            response = completion.choices[0].message.content
            print('Image description:', response)
            return response
            
        except Exception as e:
            print(f"Image description error: {e}")
            return ""

    def analyze_text_for_privacy(self, text_description):
        """
        Analyze text description for privacy information using LLM
        Args:
            text_description (str): Text description to analyze
        Returns:
            str: JSON response with privacy detection result
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a privacy analysis assistant. Analyze the provided text description and determine if it describes content that contains sensitive personal information such as Identity documents (ID cards, student cards, passports, etc.),Handwritten notes (with phone numbers, emails, home addresses, or passwords,Digital screens showing messages,and Financial objects (bank cards, passbooks, etc.). Reply only True if privacy risks exist, False otherwise."},
                    {"role": "user", "content": f"Analyze this description for privacy risks: {text_description}"}
                ],
                temperature=self.temperature
            )
            response = completion.choices[0].message.content
            print('Privacy analysis response:', response)
            
            reply = response.strip().lower()
            is_privacy = "true" in reply
            return json.dumps({"privacy": is_privacy, "description": text_description})
            
        except Exception as e:
            print(f"Text privacy analysis error: {e}")
            return json.dumps({"privacy": False, "error": str(e), "description": text_description})
    
    def query_with_image(self, image_path, msg="Please analyze whether this image contains any personal or sensitive information.", try_num=0, icl_num=0):
        """
        Convenience method for querying with image
        Args:
            msg (str): Text message
            image_path (str): Path to the image file
            try_num (int): Retry attempt number
            icl_num (int): Optional, in-context learning parameter
        Returns:
            str: JSON response with privacy detection result
        """
        return self.query(msg, image_path, try_num, icl_num)
    
    def query_batch(self, queries, icl_num=0):
        """
        Process a batch of queries in parallel.
        Args:
            queries (list): A list of strings representing user queries.
            icl_num (int): Optional, in-context learning parameter.
        Returns:
            list: A list of responses corresponding to the input queries.
        """
        def handle_query(query):
            try:
                return self.query(query, icl_num=icl_num)
            except Exception as e:
                return f"Error: {str(e)}"
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(handle_query, queries))
        return results
    
    def query_batch_with_images(self, queries_with_images, icl_num=0):
        """
        Process a batch of queries with images in parallel.
        Args:
            queries_with_images (list): A list of tuples (msg, image_path) representing user queries with images.
            icl_num (int): Optional, in-context learning parameter.
        Returns:
            list: A list of JSON responses corresponding to the input queries.
        """
        def handle_query_with_image(query_tuple):
            try:
                msg, image_path = query_tuple
                return self.query(msg, image_path, icl_num=icl_num)
            except Exception as e:
                return json.dumps({"privacy": False, "error": str(e)})
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(handle_query_with_image, queries_with_images))
        return results


class LLaVA():
    def __init__(self, name="meta-llama/llama-4-maverick:free"):
        print('LLaVA is in use.\n')
        self.set_API_key()
        self.deployment_name = name
        self.temperature = 0.0
        print(f'self.deployment_name = {self.deployment_name}')

    def set_API_key(self):
        # Configure an OpenAI-compatible endpoint for LLaVA
        # Common setups: local vLLM/LMStudio/xtuner servers expose /v1 OpenAI-compatible API

        # Use OpenAI client with custom base_url
        self.client = OpenAI(api_key=os.environ.get("OPENROUTER_API_KEY"),
         base_url="https://openrouter.ai/api/v1")



    def query(self, image_path=None, try_num=0, icl_num=0):
        msg = "Please analyze whether this image contains any personal or sensitive information."
        try:
            if image_path:
                return self.__do_query_with_image(msg, image_path, icl_num)
            else:
                return self.__do_query(msg, icl_num)
        except openai.BadRequestError:
            return json.dumps({"privacy": False, "error": "BadRequestError"})
        except openai.RateLimitError:
            print(f"RateLimitError, waiting for 10 seconds...")
            time.sleep(10)
            return self.query(msg, image_path, try_num+1, icl_num)

    def __do_query(self, msg, icl_num=0):
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": "You are a privacy and security detection assistant. The user will upload an image. Please determine whether the image contains sensitive personal information such as ID cards, bank cards, passports, driver's licenses, social security cards, phone numbers, addresses, or email addresses. If it does, reply True, otherwise reply False. Only reply True or False."},
                {"role": "user", "content": msg}
            ],
            temperature=self.temperature
        )
        response = completion.choices[0].message.content
        return response

    def __do_query_with_image(self, msg, image_path, icl_num=0):
        """
        Query LLaVA with both text and image input using an OpenAI-compatible API
        Returns a JSON string: {"privacy": <bool>}
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            if image_b64 is not None:
                print('image success.')

            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an assistant for privacy risk detection in AR images. The input is an image where any detected text has been blurred, so you cannot directly read the exact words. Instead, follow a three-step reasoning process: 1. Scene Description: Briefly describe the environment and objects in the image to understand the context. (e.g., livingroom, office desk, computer screen, handwritten notes, etc.)2. Text Topic Inference: For each blurred text region, infer the most likely topic or type of information based on its position, surrounding objects, and overall scene context. For example, blurred text on a plastic card might be an ID card, on a sticky note it might be a phone number, on a computer screen it could be an email or resume.3. Privacy Risk Assessment: Determine if the inferred text is likely to contain sensitive personal or financial information. The following categories should be considered privacy risks:(1)Identity documents (ID cards, student cards, passports, etc.)(2)Handwritten notes with phone numbers, emails, home addresses, or passwords(3)Digital screens (computer/phone) showing messages, forms, resumes, transcripts, etc.(4)Financial objects (bank cards, passbooks, etc.) Only reply True or False for the user's question."},
                    {"role": "user", "content": [
                        {"type": "text", "text": msg},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],
                temperature=self.temperature
            )
            response = completion.choices[0].message.content
            print('response:', response)
            try:
                reply = response.strip().lower()
                is_privacy = "true" in reply
            except Exception:
                is_privacy = False
            return json.dumps({"privacy": is_privacy})
        except openai.APIConnectionError as e:
            print(f"API connection error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except openai.RateLimitError as e:
            print(f"RateLimitError: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except openai.APIError as e:
            print(f"API error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except Exception as e:
            print(f"unknown error: {e}")
            return json.dumps({"privacy": False, "error": str(e)})

    def query_with_image(self, image_path, msg="Please analyze whether this image contains any personal or sensitive information.", try_num=0, icl_num=0):
        return self.query(image_path=image_path, try_num=try_num, icl_num=icl_num)

    def query_batch(self, queries, icl_num=0):
        def handle_query(query):
            try:
                return self.query(query, icl_num=icl_num)
            except Exception as e:
                return f"Error: {str(e)}"
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(handle_query, queries))
        return results

    def query_batch_with_images(self, queries_with_images, icl_num=0):
        def handle_query_with_image(query_tuple):
            try:
                msg, image_path = query_tuple
                return self.query(msg, image_path, icl_num=icl_num)
            except Exception as e:
                return json.dumps({"privacy": False, "error": str(e)})
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(handle_query_with_image, queries_with_images))
        return results


def decode_predictions(scores, geometry, confThreshold=0.5):
    (numRows, numCols) = scores.shape[2:4]
    rects = []
    confidences = []

    for y in range(numRows):
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]

        for x in range(numCols):
            if scoresData[x] < confThreshold:
                continue

            offsetX, offsetY = x * 4.0, y * 4.0
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)

            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]

            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)

            rects.append((startX, startY, endX, endY))
            confidences.append(float(scoresData[x]))

    return rects, confidences

def EAST_text_detect_box(img_path, num_samples=7, crop_size=320, conf_threshold=0.5, nms_threshold=0.4, seed=None, sampling_mode='random', tmp_dir=None):
    # === Load the pretrained EAST model ===
    
    net = net = cv2.dnn.readNet(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frozen_east_text_detection.pb'))
    
    # === Load image ===
    image = cv2.imread(img_path)
    if image is None:
        print("can not read image")
        return []
    orig = image.copy()
    (H, W) = image.shape[:2]
    print(H, W)

    rng = np.random.RandomState(seed)

    # Prepare accumulators
    all_boxes_list = []

    if sampling_mode == 'random':
        # Determine actual crop dimensions (handle images smaller than crop_size)
        crop_w = min(W, crop_size)
        crop_h = min(H, crop_size)

        for _ in range(int(num_samples)):
            # Randomly choose top-left corner for the crop
            if W - crop_w > 0:
                x0 = int(rng.randint(0, W - crop_w + 1))
            else:
                x0 = 0
            if H - crop_h > 0:
                y0 = int(rng.randint(0, H - crop_h + 1))
            else:
                y0 = 0

            crop = image[y0:y0 + crop_h, x0:x0 + crop_w]

            # Resize crop to EAST expected size (320x320)
            newW, newH = (320, 320)
            rW = crop_w / float(newW)
            rH = crop_h / float(newH)

            resized = cv2.resize(crop, (newW, newH))
            blob = cv2.dnn.blobFromImage(
                resized, 1.0, (newW, newH), (123.68, 116.78, 103.94), swapRB=True, crop=False
            )

            net.setInput(blob)
            (scores, geometry) = net.forward([
                "feature_fusion/Conv_7/Sigmoid",
                "feature_fusion/concat_3",
            ])

            rects, confidences = decode_predictions(scores, geometry)
            boxes = cv2.dnn.NMSBoxes(rects, confidences, conf_threshold, nms_threshold)

            if len(boxes) > 0:
                for i in boxes.flatten():
                    (sx, sy, ex, ey) = rects[i]

                    # Map back to crop coordinates (undo resize)
                    startX = int(sx * rW)
                    startY = int(sy * rH)
                    endX = int(ex * rW)
                    endY = int(ey * rH)

                    # Shift to original image coordinates using crop offset
                    startX += x0
                    endX += x0
                    startY += y0
                    endY += y0

                    # Clamp to original image bounds
                    startX = max(0, min(W - 1, startX))
                    endX = max(0, min(W - 1, endX))
                    startY = max(0, min(H - 1, startY))
                    endY = max(0, min(H - 1, endY))

                    # Draw and collect
                    cv2.rectangle(orig, (startX, startY), (endX, endY), (0, 255, 0), 2)
                    box_list = [startX, startY, endX, startY, startX, endY, endX, endY]
                    all_boxes_list.append(box_list)
            else:
                continue
                # print('did not detect the text in this crop!')
    elif sampling_mode == 'grid':
        # Tile the image into 320x320 patches; pad border patches to 320x320 without scaling
        tile = int(crop_size)
        for y0 in range(0, H, tile):
            for x0 in range(0, W, tile):
                actual_w = min(tile, W - x0)
                actual_h = min(tile, H - y0)

                # Extract actual crop
                crop = image[y0:y0 + actual_h, x0:x0 + actual_w]

                # Create padded 320x320 canvas and place crop at top-left
                canvas = np.zeros((tile, tile, 3), dtype=image.dtype)
                canvas[0:actual_h, 0:actual_w] = crop

                # Prepare blob directly from padded canvas (already 320x320)
                blob = cv2.dnn.blobFromImage(
                    canvas, 1.0, (tile, tile), (123.68, 116.78, 103.94), swapRB=True, crop=False
                )

                net.setInput(blob)
                (scores, geometry) = net.forward([
                    "feature_fusion/Conv_7/Sigmoid",
                    "feature_fusion/concat_3",
                ])

                rects, confidences = decode_predictions(scores, geometry)
                boxes = cv2.dnn.NMSBoxes(rects, confidences, conf_threshold, nms_threshold)

                if len(boxes) > 0:
                    for i in boxes.flatten():
                        (sx, sy, ex, ey) = rects[i]

                        # Because we used padding (no scaling), map directly within actual area
                        # Filter out boxes that fall entirely outside the actual crop area (in padded region)
                        if sx >= actual_w or sy >= actual_h:
                            continue
                        # Clamp to actual region bounds before mapping
                        sx = max(0, min(actual_w - 1, sx))
                        ex = max(0, min(actual_w - 1, ex))
                        sy = max(0, min(actual_h - 1, sy))
                        ey = max(0, min(actual_h - 1, ey))

                        startX = int(sx) + x0
                        startY = int(sy) + y0
                        endX = int(ex) + x0
                        endY = int(ey) + y0

                        # Clamp to original image bounds
                        startX = max(0, min(W - 1, startX))
                        endX = max(0, min(W - 1, endX))
                        startY = max(0, min(H - 1, startY))
                        endY = max(0, min(H - 1, endY))

                        cv2.rectangle(orig, (startX, startY), (endX, endY), (0, 255, 0), 2)
                        box_list = [startX, startY, endX, startY, startX, endY, endX, endY]
                        all_boxes_list.append(box_list)
                else:
                    # print('did not detect the text in this tile!')
                    continue
    else:
        print("use 'random'")
        return EAST_text_detect_box(img_path, num_samples=num_samples, crop_size=crop_size, conf_threshold=conf_threshold, nms_threshold=nms_threshold, seed=seed, sampling_mode='random')

    
    if tmp_dir:
        basename, _ =os.path.splitext(os.path.basename(img_path))
        output_path = os.path.join(tmp_dir,f"{basename}_detect_multi.jpg")
    else:
        base, ext = os.path.splitext(img_path)
        output_path = f"{base}_detect_multi{ext}"
    cv2.imwrite(output_path, orig)
    print(f"save detected image: {output_path}")
    return all_boxes_list




def elastic_distort_boxes(image_path, boxes, blur_radius=5, alpha=1000, sigma=40, random_state=None, tmp_dir=None):

    """
    First, perform Gaussian blurring on the pixels within the "boxes" area of the original image, and then apply elastic deformation to make the original text information unrecognizable by AI.
    :param image_path: Path of the original image
    :param boxes: List of text boxes, in the format [[x1, y1, x2, y2, x3, y3, x4, y4], ...], consistent with the output of EAST_text_detect_box
    :param blur_radius: Radius of Gaussian blurring, used for preprocessing the text box area
    :param alpha: Strength of elastic deformation
    :param sigma: Parameter of Gaussian filtering
    :param random_state: Random seed
    :return: None, the processed image will be saved 
    """
    if random_state is None:
        random_state = np.random.RandomState(None)
    image = cv2.imread(image_path)
    if image is None:
        print("can not read image")
        return False
    h, w = image.shape[:2]
    
    
    processed_image = image.copy()
    
    # process every box
    for box in boxes:
        
        box_coords = np.array(box, dtype=np.int32).reshape(-1, 2)
        
        # get the box
        x_coords = box_coords[:, 0]
        y_coords = box_coords[:, 1]
        x_min, x_max = np.clip(np.min(x_coords), 0, w-1), np.clip(np.max(x_coords), 0, w-1)
        y_min, y_max = np.clip(np.min(y_coords), 0, h-1), np.clip(np.max(y_coords), 0, h-1)
        
        
        text_region = processed_image[y_min:y_max+1, x_min:x_max+1]
        
        if text_region.size > 0:
            # gaussian blurring
            blurred_region = cv2.GaussianBlur(text_region, (0, 0), blur_radius)
            
            # elastic distortion
            region_h, region_w = text_region.shape[:2]
            
            
            dx = (random_state.rand(region_h, region_w) * 2 - 1)
            dy = (random_state.rand(region_h, region_w) * 2 - 1)
            dx = cv2.GaussianBlur(dx, (0, 0), sigma) * alpha
            dy = cv2.GaussianBlur(dy, (0, 0), sigma) * alpha
            
            # create map array
            map_x, map_y = np.meshgrid(np.arange(region_w), np.arange(region_h))
            map_x = map_x.astype(np.float32)
            map_y = map_y.astype(np.float32)
            
            
            map_x_distorted = map_x + dx.astype(np.float32)
            map_y_distorted = map_y + dy.astype(np.float32)
            
            
            map_x_distorted = np.clip(map_x_distorted, 0, region_w - 1).astype(np.float32)
            map_y_distorted = np.clip(map_y_distorted, 0, region_h - 1).astype(np.float32)
            
            # blurring image
            try:
                distorted_region = cv2.remap(
                    blurred_region, 
                    map_x_distorted, 
                    map_y_distorted, 
                    interpolation=cv2.INTER_LINEAR, 
                    borderMode=cv2.BORDER_REFLECT
                )
            except cv2.error as e:
                print(f"cv2.remap error: {e}")
                
                distorted_region = blurred_region
            
            
            processed_image[y_min:y_max+1, x_min:x_max+1] = distorted_region
    
    # save blurred image
    if tmp_dir:
        basename, _ =os.path.splitext(os.path.basename(image_path))
        output_path = os.path.join(tmp_dir,f"{basename}_blur_elastic.jpg")
    else:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_blur_elastic{ext}"
    cv2.imwrite(output_path, processed_image)
    print(f"blurred image was saved to: {output_path}")
    return output_path




def ensure_image_size(image_path, threshold_kb=500, target_kb=100, min_quality=20, tmp_dir=None):
    """
    Ensure the image at image_path is under target_kb if its original size exceeds threshold_kb.
    - If the file size > threshold_kb, compress using JPEG quality reduction and proportional scaling.
    - Returns the path to the (possibly new) image file. If no compression needed or on failure, returns the original path.
    """
    try:
        if not os.path.isfile(image_path):
            print("there is not the image:", image_path)
            return image_path

        original_size_kb = os.path.getsize(image_path) / 1024.0
        if original_size_kb <= float(threshold_kb):
            return image_path

        image = cv2.imread(image_path)
        if image is None:
            print("can not read image correctly:", image_path)
            return image_path

        if tmp_dir:
            basename, _ =os.path.splitext(os.path.basename(image_path))
            output_path = os.path.join(tmp_dir,f"{basename}_compressed.jpg")
        else:
            base, _ = os.path.splitext(image_path)
            output_path = f"{base}_compressed.jpg"

        # Start with reasonable defaults; iterate reducing quality first, then scale
        quality = 85
        scale = 1.0
        last_buffer = None

        for _ in range(12):
            # Resize proportionally when scale < 1
            if scale < 0.999:
                new_w = max(1, int(image.shape[1] * scale))
                new_h = max(1, int(image.shape[0] * scale))
                resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                resized = image

            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
            ok, buffer = cv2.imencode('.jpg', resized, encode_params)
            if not ok:
                break
            last_buffer = buffer

            size_kb = len(buffer) / 1024.0
            if size_kb <= float(target_kb):
                with open(output_path, 'wb') as f:
                    f.write(buffer)
                print(f"compressed at {size_kb:.1f}KB: {output_path}")
                return output_path

            # Reduce quality down to min_quality, then start scaling down
            if quality > min_quality:
                quality = max(min_quality, quality - 10)
            else:
                # Scale down and slightly reset quality to balance detail/size
                scale *= 0.85
                quality = min(80, quality + 5)

        # If loop ends without meeting target, write the best attempt
        if last_buffer is not None:
            with open(output_path, 'wb') as f:
                f.write(last_buffer)
            approx_kb = len(last_buffer) / 1024.0
            print(f"can not compress more, only {approx_kb:.1f}KB: {output_path}")
            return output_path

        return image_path
    except Exception as e:
        print("compress error:", str(e))
        return image_path






def get_supported_image_extensions():
    """
    Get list of supported image file extensions
    """
    return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']

def is_image_file(file_path):
    """
    Check if file is a supported image format
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in get_supported_image_extensions()

def process_single_image(image_path, mode, gpt_model=None, tmp_dir=None):
    """
    Process a single image and return privacy detection result
    Args:
        image_path (str): Path to the image file
        mode (str): Processing mode ('full', 'different prompt', 'no VLM', 'one-step', etc.)
        gpt_model: Pre-initialized GPT model (optional, for efficiency)
    Returns:
        dict: Processing result with privacy detection outcome
    """
    try:
        print(f"Processing: {os.path.basename(image_path)}")
        
        if mode == 'full':
            compressed_path = ensure_image_size(image_path, target_kb=200, tmp_dir=tmp_dir)
            box_list = EAST_text_detect_box(compressed_path, sampling_mode='grid', tmp_dir=tmp_dir)
            processed_path = elastic_distort_boxes(compressed_path, box_list, tmp_dir=tmp_dir)
            result = check_privacy(processed_path)
            result = json.loads(result) if isinstance(result, str) else result
            

        elif mode == 'full-gpt4o':
            compressed_path = ensure_image_size(image_path, target_kb=200, tmp_dir=tmp_dir)
            box_list = EAST_text_detect_box(compressed_path, sampling_mode='grid', tmp_dir=tmp_dir)
            processed_path = elastic_distort_boxes(compressed_path, box_list, tmp_dir=tmp_dir)
            result = check_privacy(processed_path, vlm_mode="gpt-4o")
            result = json.loads(result) if isinstance(result, str) else result    
        elif mode == 'llava':
            compressed_path = ensure_image_size(image_path, target_kb=200, tmp_dir=tmp_dir)
            box_list = EAST_text_detect_box(compressed_path, sampling_mode='grid', tmp_dir=tmp_dir)
            processed_path = elastic_distort_boxes(compressed_path, box_list, tmp_dir=tmp_dir)
            result = check_privacy(processed_path,vlm_mode='llava4')
            result = json.loads(result) if isinstance(result, str) else result
        elif mode == 'only VLM':
            compressed_path = ensure_image_size(image_path, target_kb=200, tmp_dir=tmp_dir)
            result = check_privacy(compressed_path)
            result = json.loads(result) if isinstance(result, str) else result
            
        elif mode == 'different prompt':
            if gpt_model is None:
                gpt_model = GPTAzure("gpt-4o-mini")
            compressed_path = ensure_image_size(image_path, target_kb=200, tmp_dir=tmp_dir)
            box_list = EAST_text_detect_box(compressed_path, sampling_mode='grid', tmp_dir=tmp_dir)
            processed_path = elastic_distort_boxes(compressed_path, box_list, tmp_dir=tmp_dir)
            description = gpt_model.describe_image(processed_path)
            result = gpt_model.analyze_text_for_privacy(description)
            result = json.loads(result) if isinstance(result, str) else result
            


        elif mode == 'ideal':

            image_path=ensure_image_size(image_path, threshold_kb=300,target_kb=200,tmp_dir=tmp_dir)
            result=check_privacy(image_path)
            print('json:',result)

            
        else:
            result = {"privacy": False, "error": f"Unknown mode: {mode}"}
        
        return {
            "image_path": image_path,
            "privacy_detected": result.get("privacy", False),
            "result_details": result,
            "processing_mode": mode,
            "success": True
        }
        
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return {
            "image_path": image_path,
            "privacy_detected": False,
            "result_details": {"error": str(e)},
            "processing_mode": mode,
            "success": False
        }

def classify_result(true_label, predicted_label):
    """
    Classify prediction result as TP/TN/FP/FN
    Args:
        true_label (bool): True privacy label (True for positive folder, False for negative folder)
        predicted_label (bool): Predicted privacy result
    Returns:
        str: Classification result ('TP', 'TN', 'FP', 'FN')
    """
    if true_label and predicted_label:
        return 'TP'  # True Positive
    elif not true_label and not predicted_label:
        return 'TN'  # True Negative
    elif not true_label and predicted_label:
        return 'FP'  # False Positive
    elif true_label and not predicted_label:
        return 'FN'  # False Negative

def batch_process_images(dataset_folder, mode='full', output_excel=None, tmp_dir=None):
    """
    Process all images in positive/negative folders and generate evaluation results
    Args:
        dataset_folder (str): Path to dataset folder containing 'positive' and 'negative' subfolders
        mode (str): Processing mode
        output_excel (str): Output Excel file path (optional)
    Returns:
        pd.DataFrame: Results dataframe
    """
    if not os.path.exists(dataset_folder):
        raise ValueError(f"Dataset folder does not exist: {dataset_folder}")
    
    if mode=='ideal':
        positive_folder = os.path.join(dataset_folder, 'positive_ideal')
        negative_folder = os.path.join(dataset_folder, 'negative')
    else:
        positive_folder = os.path.join(dataset_folder, 'positive')
        negative_folder = os.path.join(dataset_folder, 'negative')
    

    results = []
    
    # Initialize GPT model once for efficiency (if needed)
    gpt_model = None
    if mode in ['different prompt', 'only VLM']:
        gpt_model = GPTAzure("gpt-4o-mini")
    
    # Process positive images (ground truth: privacy = True)
    print(f"\n=== Processing POSITIVE images ===")
    if os.path.exists(positive_folder):
        positive_images = []
        for ext in get_supported_image_extensions():

            positive_images.extend(glob.glob(os.path.join(positive_folder, f"*{ext}")))

        
        for img_path in positive_images:
            if is_image_file(img_path):
                result = process_single_image(img_path, mode, gpt_model,tmp_dir=tmp_dir)
                classification = classify_result(True, result["privacy_detected"])
                
                results.append({
                    'image_name': os.path.basename(img_path),
                    'image_path': img_path,
                    'folder': 'positive',
                    'ground_truth': True,
                    'predicted': result["privacy_detected"],
                    'classification': classification,
                    'processing_mode': mode,
                    'success': result["success"],
                    'result_details': str(result["result_details"])
                })
    else:
        print(f"Positive folder does not exist: {positive_folder}")
    # Process negative images (ground truth: privacy = False)
    print(f"\n=== Processing NEGATIVE images ===")
    if os.path.exists(negative_folder):
        negative_images = []
        for ext in get_supported_image_extensions():
            negative_images.extend(glob.glob(os.path.join(negative_folder, f"*{ext}")))

        
        for img_path in negative_images:
            if is_image_file(img_path):
                result = process_single_image(img_path, mode, gpt_model,tmp_dir=tmp_dir)
                classification = classify_result(False, result["privacy_detected"])
                
                results.append({
                    'image_name': os.path.basename(img_path),
                    'image_path': img_path,
                    'folder': 'negative',
                    'ground_truth': False,
                    'predicted': result["privacy_detected"],
                    'classification': classification,
                    'processing_mode': mode,
                    'success': result["success"],
                    'result_details': str(result["result_details"])
                })
    else:
        print(f"Negative folder does not exist: {positive_folder}")
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Calculate metrics
    tp = len(df[df['classification'] == 'TP'])
    tn = len(df[df['classification'] == 'TN'])
    fp = len(df[df['classification'] == 'FP'])
    fn = len(df[df['classification'] == 'FN'])
    
    # Calculate performance metrics
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Add summary statistics
    summary_stats = {
        'Total Images': len(df),
        'True Positives (TP)': tp,
        'True Negatives (TN)': tn,
        'False Positives (FP)': fp,
        'False Negatives (FN)': fn,
        'Accuracy': f"{accuracy:.4f}",
        'Precision': f"{precision:.4f}",
        'Recall': f"{recall:.4f}",
        'F1 Score': f"{f1_score:.4f}",
        'Processing Mode': mode,
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    print(f"\n=== EVALUATION RESULTS ===")
    for key, value in summary_stats.items():
        print(f"{key}: {value}")
    
    # Save to Excel if path provided
    if output_excel:
        save_results_to_excel(df, summary_stats, output_excel)
    
    return df, summary_stats

def save_results_to_excel(df, summary_stats, output_path):
    """
    Save results to Excel file with multiple sheets
    """
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Save detailed results
            df.to_excel(writer, sheet_name='Detailed Results', index=False)
            
            # Save summary statistics
            summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Save classification counts
            classification_counts = df['classification'].value_counts().reset_index()
            classification_counts.columns = ['Classification', 'Count']
            classification_counts.to_excel(writer, sheet_name='Classification Counts', index=False)
        
        print(f"\nResults saved to: {output_path}")
        
    except Exception as e:
        print(f"Error saving Excel file: {e}")

def merge_dataset_results(method_name, data_dir):
    """
    Merge results from multiple dataset subfolders.
    Args:
        method_name (str): The method name used in the excel file naming.
        data_dir (str): The parent directory containing subfolders for each dataset.
    Saves:
        An Excel file in data_dir named '{method_name}.xlsx' with merged summary.
    """
    import os
    import pandas as pd

    # Initialize counters
    total_tp = 0
    total_tn = 0
    total_fp = 0
    total_fn = 0
    sub_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    summary_rows = []

    for sub_dir in sub_dirs:
        if sub_dir =='llava_next':
            continue
        excel_path = os.path.join(data_dir, sub_dir, f"{sub_dir}_{method_name}.xlsx")
        if not os.path.exists(excel_path):
            print(f"Warning: Excel file not found for {sub_dir}: {excel_path}")
            continue
        try:
            df = pd.read_excel(excel_path, sheet_name='Summary', index_col=0)
            # The sheet is expected to have 'Metric' as index and 'Value' as column
            # Try to get values for TP, TN, FP, FN
            tp = int(df.loc['True Positives (TP)', 'Value'])
            tn = int(df.loc['True Negatives (TN)', 'Value'])
            fp = int(df.loc['False Positives (FP)', 'Value'])
            fn = int(df.loc['False Negatives (FN)', 'Value'])
            total_tp += tp
            total_tn += tn
            total_fp += fp
            total_fn += fn
            summary_rows.append({
                'Dataset': sub_dir,
                'TP': tp,
                'TN': tn,
                'FP': fp,
                'FN': fn
            })
        except Exception as e:
            print(f"Error reading summary from {excel_path}: {e}")

    # Calculate metrics
    total = total_tp + total_tn + total_fp + total_fn
    accuracy = (total_tp + total_tn) / total if total > 0 else 0
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Prepare merged summary DataFrame
    merged_summary = [
        ['Total Images', total],
        ['True Positives (TP)', total_tp],
        ['True Negatives (TN)', total_tn],
        ['False Positives (FP)', total_fp],
        ['False Negatives (FN)', total_fn],
        ['Accuracy', f"{accuracy:.4f}"],
        ['Precision', f"{precision:.4f}"],
        ['Recall', f"{recall:.4f}"],
        ['F1 Score', f"{f1_score:.4f}"],
        ['Method', method_name]
    ]
    merged_summary_df = pd.DataFrame(merged_summary, columns=['Metric', 'Value'])

    # Save to Excel
    output_path = os.path.join(data_dir, f"{method_name}.xlsx")
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Save merged summary
            merged_summary_df.to_excel(writer, sheet_name='Merged Summary', index=False)
            # Save per-dataset counts
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Per Dataset Counts', index=False)
        print(f"Merged results saved to: {output_path}")
    except Exception as e:
        print(f"Error saving merged Excel file: {e}")


if __name__ == '__main__':
    import time

    # ==========================================================================
    # CONFIGURATION SECTION - Modify these settings
    # ==========================================================================
    
    # Choose processing mode:
    # - 'single': Process single image
    # - 'batch': Process entire dataset folder with positive/negative subfolders
    # - 'merge' : merge all results from different datasets
    run_mode='batch'
    
    # Choose image processing mode
    # - 'full': PrivAR with gpt-4o-mini
    # - 'full-gpt4o': PrivAR with gpt-4o
    # - 'llava': PrivAR with LLaMA-4-Mav.
    # - 'only VLM': PrivAR without obfuscation
    # - 'different prompt': Scene captioning-based
    # - 'ideal' : Oracle-guided obfuscation
    pipeline_mode = 'full' 
    image_path = 'test.jpg'


    root_dir = 'Dataset'
    # ==========================================================================
    
    if run_mode == 'single':
        print(f"=== SINGLE IMAGE MODE: {pipeline_mode.upper()} ===")
        
        if pipeline_mode == 'full':
            start_time=time.time()
            image_path=ensure_image_size(image_path,target_kb=200)
            box_list=EAST_text_detect_box(image_path,sampling_mode='grid')
            processed_path=elastic_distort_boxes(image_path,box_list)
            json_result=check_privacy(processed_path)
            print('json:',json_result)
            if isinstance(json_result, dict):
                json_result['box_list']=box_list
            print('json:',json_result)
            end_time=time.time()
            print('all time:',end_time-start_time)

        elif pipeline_mode == 'full-gpt4o':
            start_time=time.time()
            image_path=ensure_image_size(image_path,target_kb=200)
            box_list=EAST_text_detect_box(image_path,sampling_mode='grid')
            processed_path=elastic_distort_boxes(image_path,box_list)
            json_result=check_privacy(processed_path,vlm_mode='gpt-4o')
            print('json:',json_result)
            if isinstance(json_result, dict):
                json_result['box_list']=box_list
            print('json:',json_result)
            end_time=time.time()
            print('all time:',end_time-start_time)

        elif pipeline_mode == 'llava':
            start_time=time.time()
            image_path=ensure_image_size(image_path,target_kb=200)
            box_list=EAST_text_detect_box(image_path,sampling_mode='grid')
            processed_path=elastic_distort_boxes(image_path,box_list)
            json_result=check_privacy(processed_path,vlm_mode='llava4')
            print('json:',json_result)
            if isinstance(json_result, dict):
                json_result['box_list']=box_list
            print('json:',json_result)
            end_time=time.time()
            print('all time:',end_time-start_time)
            
        elif pipeline_mode == 'only VLM':
            start_time=time.time()
            image_path=ensure_image_size(image_path,target_kb=200)
            json_result=check_privacy(image_path)
            print('json:',json_result)
            end_time=time.time()
            print('all time:',end_time-start_time)
            
        elif pipeline_mode=='ideal':
            start_time=time.time()
            image_path_gt=''
            image_path=ensure_image_size(image_path_gt,target_kb=200)
            json_result=check_privacy(image_path)
            print('json:',json_result)
            end_time=time.time()
            print('all time:',end_time-start_time)
            
        elif pipeline_mode == 'different prompt':
            print("=== Different Prompt Mode ===")
            start_time=time.time()
            
            # Step 1: Compress image
            image_path=ensure_image_size(image_path,target_kb=200)
            print(f"Image compressed: {image_path}")
            
            # Step 2: Detect text boxes using EAST
            box_list=EAST_text_detect_box(image_path,sampling_mode='grid')
            print(f"Detected {len(box_list)} text boxes")
            
            # Step 3: Apply blur to text regions
            processed_path=elastic_distort_boxes(image_path,box_list)
            print(f"Processed image saved: {processed_path}")
            
            # Step 4: Get image description using VLM
            vlm_model = GPTAzure("gpt-4o-mini")
            description = vlm_model.describe_image(processed_path)
            print(f"Image description: {description}")
            
            # Step 5: Analyze description for privacy using LLM
            json_result = vlm_model.analyze_text_for_privacy(description)
            print('Final result:', json_result)
            
            end_time=time.time()
            print('all time:',end_time-start_time)
            

            

            
    elif run_mode == 'batch':
        print(f"=== BATCH PROCESSING MODE: {pipeline_mode.upper()} ===")

        for subset in os.listdir(root_dir):
            dataset_folder = os.path.join(root_dir, subset)
            if not os.path.isdir(dataset_folder):
                continue

            tmp_dir = os.path.join(dataset_folder, 'temp')
            output_excel_path = os.path.join(dataset_folder, f'{subset}_{pipeline_mode}.xlsx')
            os.makedirs(tmp_dir, exist_ok=True)


            print(f"Dataset folder: {dataset_folder}")
            print(f"Output Excel: {output_excel_path}")


            try:
                start_time = time.time()

                # Run batch processing
                results_df, summary_stats = batch_process_images(
                    dataset_folder=dataset_folder,
                    mode=pipeline_mode,
                    output_excel=output_excel_path,
                    tmp_dir=tmp_dir
                )

                end_time = time.time()

                print(f"\n=== BATCH PROCESSING COMPLETED ===")
                print(f"Total processing time: {end_time - start_time:.2f} seconds")
                print(f"Processed {len(results_df)} images")
                print(f"Results saved to: {output_excel_path}")

            except Exception as e:
                print(f"Error in batch processing: {e}")
                import traceback
                traceback.print_exc()
    
    elif run_mode == 'merge':
        merge_dataset_results(method_name=pipeline_mode, 
                              data_dir=root_dir)
    else:
        print(f"Invalid run_mode: {run_mode}. Use 'single' or 'batch'.")




