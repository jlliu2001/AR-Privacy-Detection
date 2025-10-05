from flask import Flask, request, jsonify
import tempfile
import os
import subprocess
import json
from openai import OpenAI
from openai import AzureOpenAI
import openai
# import tiktoken
import time
import base64
import json
from concurrent.futures import ThreadPoolExecutor
import sys

import sys
import requests
import json
import os
import cv2
import numpy as np
import pytesseract as ts


app = Flask(__name__)
@app.route('/check_privacy', methods=['POST'])
def check_privacy():
    print("check_privacy")
    gpt = GPTAzure("gpt-4o-mini")
    print('gpt loaded!')
    EAST_model_path="your EAST model path"
    
    if 'image' not in request.files:
        return jsonify({'privacy': False, 'error': 'No image uploaded'}), 400
    image = request.files['image']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name
    try:

        box_list,box_list_normalized=EAST_text_detect_box(tmp_path,sampling_mode='grid',model_path=EAST_model_path)

        processed_path=elastic_distort_boxes(tmp_path,box_list)
        result=gpt.query(image_path=processed_path)

        result_json = json.loads(result)
        result_json["box_list"]=box_list_normalized
        

        print('result:', result_json)
    except Exception as e:
        print('Error:', str(e))
        os.remove(tmp_path)
        return jsonify({'privacy': False, 'error': str(e)}), 500
    os.remove(tmp_path)
    return jsonify(result_json)


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


def EAST_text_detect_box(img_path, num_samples=7, crop_size=320, conf_threshold=0.5, nms_threshold=0.4, seed=None, sampling_mode='random', tmp_dir=None, model_path="E:/Study/model/frozen_east_text_detection.pb"):
    # === Load the pretrained EAST model ===
    net = cv2.dnn.readNet(model_path)

    # === Load image ===
    image = cv2.imread(img_path)
    if image is None:
        print("无法读取图像")
        return []
    orig = image.copy()
    (H, W) = image.shape[:2]
    print(H, W)

    rng = np.random.RandomState(seed)

    # Prepare accumulators
    all_boxes_list = []
    all_boxes_list_normalized = []

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
                    all_boxes_list_normalized.append([startX/W, startY/H, endX/W, startY/H, startX/W, endY/H, endX/W, endY/H])
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
                        # all_boxes_list_normalized.append([1-startX/W, 1-startY/H, 1-endX/W, 1-startY/H, 1-startX/W, 1-endY/H, 1-endX/W, 1-endY/H])
                        all_boxes_list_normalized.append([startX/W, startY/H, endX/W, startY/H, startX/W, endY/H, endX/W, endY/H])
                else:
                    # print('did not detect the text in this tile!')
                    continue
    else:
        print("未知的 sampling_mode，使用 'random'")
        return EAST_text_detect_box(img_path, num_samples=num_samples, crop_size=crop_size, conf_threshold=conf_threshold, nms_threshold=nms_threshold, seed=seed, sampling_mode='random')

    # 保存叠加了全部检测框的原图
    if tmp_dir:
        basename, _ =os.path.splitext(os.path.basename(img_path))
        output_path = os.path.join(tmp_dir,f"{basename}_detect_multi.jpg")
    else:
        base, ext = os.path.splitext(img_path)
        output_path = f"{base}_detect_multi{ext}"
    cv2.imwrite(output_path, orig)
    print(f"检测结果已保存到: {output_path}")
    return all_boxes_list,all_boxes_list_normalized


def OCR_text_detect_box(img_path):
    # img_fn ='bookseg.png'
    try:
        lang ='eng'
        boxes =ts.image_to_boxes(img_path,lang)

        # print(boxes)
        # 读取原图像
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        # boxes 是 tesseract.image_to_boxes 的输出，格式为字符串，每行一个字符及其box: char x1 y1 x2 y2 page
        boxes_list=[]
        for b in boxes.splitlines():
            b = b.strip()
            if not b:
                continue
            parts = b.split(' ')
            if len(parts) < 6:
                continue
            char, x1, y1, x2, y2, _ = parts
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            # tesseract 的 y 坐标原点在左下角，opencv 在左上角，需要转换
            y1_cv = h - y1
            y2_cv = h - y2
            # 画框
            cv2.rectangle(image, (x1, y2_cv), (x2, y1_cv), (0, 0, 255), 2)
            box_list.append([x1, y2_cv,x2, y2_cv,x1, y1_cv,x2, y1_cv])
            # 可选：在框旁边写字符
            # cv2.putText(image, char, (x1, y2_cv - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 保存标注后的图像
        base, ext = os.path.splitext(img_path)
        output_path = f"{base}_ocrbox{ext}"
        cv2.imwrite(output_path, image)
        print(f"OCR检测框已保存到: {output_path}")
        return box_list
    except Exception as e:
        return None

def elastic_distort_boxes(image_path, boxes, blur_radius=5, alpha=1000, sigma=40, random_state=None):
    """
    对原始图像在boxes区域内的像素先进行高斯模糊，然后进行弹性变形，使得原本的文字信息无法被AI还原。
    :param image_path: 原始图像路径
    :param boxes: 文本框列表，格式为[[x1, y1, x2, y2, x3, y3, x4, y4], ...]，与EAST_text_detect_box返回一致
    :param blur_radius: 高斯模糊半径，用于预处理文本框区域
    :param alpha: 弹性变形强度
    :param sigma: 高斯滤波参数
    :param random_state: 随机种子
    :return: None，处理后图像会被保存
    """
    if random_state is None:
        random_state = np.random.RandomState(None)
    image = cv2.imread(image_path)
    if image is None:
        print("无法读取图像")
        return False
    h, w = image.shape[:2]
    
    # 创建处理后的图像副本
    processed_image = image.copy()
    
    # 对每个检测到的文本框进行处理
    for box in boxes:
        # 将box坐标转换为整数
        box_coords = np.array(box, dtype=np.int32).reshape(-1, 2)
        
        # 获取文本框的边界框
        x_coords = box_coords[:, 0]
        y_coords = box_coords[:, 1]
        x_min, x_max = np.clip(np.min(x_coords), 0, w-1), np.clip(np.max(x_coords), 0, w-1)
        y_min, y_max = np.clip(np.min(y_coords), 0, h-1), np.clip(np.max(y_coords), 0, h-1)
        
        # 提取文本框区域
        text_region = processed_image[y_min:y_max+1, x_min:x_max+1]
        
        if text_region.size > 0:
            # 第一步：对文本框区域进行高斯模糊
            blurred_region = cv2.GaussianBlur(text_region, (0, 0), blur_radius)
            
            # 第二步：对模糊后的区域进行弹性变形
            region_h, region_w = text_region.shape[:2]
            
            # 生成弹性形变场
            dx = (random_state.rand(region_h, region_w) * 2 - 1)
            dy = (random_state.rand(region_h, region_w) * 2 - 1)
            dx = cv2.GaussianBlur(dx, (0, 0), sigma) * alpha
            dy = cv2.GaussianBlur(dy, (0, 0), sigma) * alpha
            
            # 创建映射数组 - 确保类型完全正确
            map_x, map_y = np.meshgrid(np.arange(region_w), np.arange(region_h))
            map_x = map_x.astype(np.float32)
            map_y = map_y.astype(np.float32)
            
            # 应用弹性变形
            map_x_distorted = map_x + dx.astype(np.float32)
            map_y_distorted = map_y + dy.astype(np.float32)
            
            # 确保映射坐标在有效范围内
            map_x_distorted = np.clip(map_x_distorted, 0, region_w - 1).astype(np.float32)
            map_y_distorted = np.clip(map_y_distorted, 0, region_h - 1).astype(np.float32)
            
            # 对模糊后的区域进行弹性变形
            try:
                distorted_region = cv2.remap(
                    blurred_region, 
                    map_x_distorted, 
                    map_y_distorted, 
                    interpolation=cv2.INTER_LINEAR, 
                    borderMode=cv2.BORDER_REFLECT
                )
            except cv2.error as e:
                print(f"cv2.remap 错误: {e}")
                print(f"map_x_distorted 类型: {map_x_distorted.dtype}, 形状: {map_x_distorted.shape}")
                print(f"map_y_distorted 类型: {map_y_distorted.dtype}, 形状: {map_y_distorted.shape}")
                # 如果 remap 失败，只使用模糊效果
                distorted_region = blurred_region
            
            # 将处理后的区域放回原图像
            processed_image[y_min:y_max+1, x_min:x_max+1] = distorted_region
    
    # 保存处理后的图像
    base, ext = os.path.splitext(image_path)
    output_path = f"{base}_blur_elastic{ext}"
    cv2.imwrite(output_path, processed_image)
    print(f"高斯模糊+弹性变形处理后的图像已保存到: {output_path}")
    return output_path

def ensure_image_size(image_path, threshold_kb=500, target_kb=100, min_quality=20):
    """
    Ensure the image at image_path is under target_kb if its original size exceeds threshold_kb.
    - If the file size > threshold_kb, compress using JPEG quality reduction and proportional scaling.
    - Returns the path to the (possibly new) image file. If no compression needed or on failure, returns the original path.
    """
    try:
        if not os.path.isfile(image_path):
            print("文件不存在:", image_path)
            return image_path

        original_size_kb = os.path.getsize(image_path) / 1024.0
        if original_size_kb <= float(threshold_kb):
            return image_path

        image = cv2.imread(image_path)
        if image is None:
            print("无法读取图像进行压缩:", image_path)
            return image_path

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
                print(f"已压缩到约 {size_kb:.1f}KB: {output_path}")
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
            print(f"未完全达到目标，已尽力压缩到约 {approx_kb:.1f}KB: {output_path}")
            return output_path

        return image_path
    except Exception as e:
        print("压缩失败:", str(e))
        return image_path




class GPTAzure():
    def __init__(self, name):
        print('GPTAzureFT is in use.\n')
        self.set_API_key()
        self.deployment_name = name
        self.temperature = 0.0
        print(f'self.deployment_name = {self.deployment_name}')
    
    def set_API_key(self):

        self.client = AzureOpenAI(
            api_key="your api key",
            api_version="your api version",
            azure_endpoint = "your api website"
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
                    {"role": "system", "content": "You are an assistant for privacy risk detection in AR images. The input is an image where any detected text has been blurred, so you cannot directly read the exact words. Instead, follow a three-step reasoning process: 1. Scene Description: Briefly describe the environment and objects in the image to understand the context. (e.g., livingroom, office desk, computer screen, handwritten notes, etc.)2. Text Topic Inference: For each blurred text region, infer the most likely topic or type of information based on its position, surrounding objects, and overall scene context. For example, blurred text on a plastic card might be an ID card, on a sticky note it might be a phone number, on a computer screen it could be an email or resume.3. Privacy Risk Assessment: Determine if the inferred text is likely to contain sensitive personal or financial information. The following categories should be considered privacy risks:(1)Identity documents (ID cards, student cards, passports, etc.)(2)Handwritten notes with phone numbers, emails, home addresses, or passwords(3)Digital screens (computer/phone) showing messages, forms, resumes, transcripts, etc.(4)Financial objects (bank cards, passbooks, etc.) Only reply True/False for the user's question."},
                    {"role": "user", "content": [
                        {"type": "text", "text": msg},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],
                temperature=self.temperature
                # max_tokens=10
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
            print(f"API连接错误: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
        except openai.RateLimitError as e:
            print(f"速率限制错误: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
                
        except openai.APIError as e:
            print(f"API错误: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
            
        except Exception as e:
            print(f"未知错误: {e}")
            return json.dumps({"privacy": False, "error": str(e)})
    
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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 