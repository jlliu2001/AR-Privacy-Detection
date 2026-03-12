from calendar import c
import os
import re
import cv2
import numpy as np
import pandas as pd
import json
import base64
import time
from openai import AzureOpenAI
import openai

# Reuse pytesseract OCR similar to pipeline.py
import pytesseract as ts



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
    
    def extract_privacy_details(self, image_path, try_num=0):
        """
        Extract specific privacy information details from image using GPT-4o
        Args:
            image_path (str): Path to the image file
            try_num (int): Retry attempt number
        Returns:
            str: JSON response with specific privacy details
        """
        msg = "Please analyze this image and extract any specific privacy information you can see. For example, if you see a phone number, please provide the exact number. If you see an ID card, please provide the specific ID number. If you see an email, please provide the exact email address. Please be as specific as possible and provide the exact values you can read. If no privacy information is visible, respond with 'No privacy information detected'."
        
        try:
            if image_path:
                return self.__do_query_with_image(msg, image_path, try_num)
            else:
                return json.dumps({"privacy_details": "No image provided", "error": "No image path"})
        except openai.BadRequestError:
            return json.dumps({"privacy_details": "BadRequestError", "error": "BadRequestError"})
        except openai.RateLimitError:
            print(f"RateLimitError, waiting for 10 seconds...")
            time.sleep(10)
            return self.extract_privacy_details(image_path, try_num+1)
    
    def __do_query_with_image(self, msg, image_path, try_num=0):
        """
        Query with both text and image input
        Args:
            msg (str): Text message
            image_path (str): Path to the image file
            try_num (int): Retry attempt number
        Returns:
            str: JSON response with privacy details
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
                    {"role": "system", "content": "You are a privacy information extraction assistant. Your task is to carefully examine the image and extract any specific privacy information that is clearly visible. This includes: phone numbers, email addresses, ID card numbers, student ID numbers, passport numbers, credit card numbers, addresses, names.transcripts,medical reports, privacy message on the computer or phone, and any other personally identifiable information. Please provide the exact values you can read, not just descriptions. If you cannot clearly read specific information, say so. Format your response as a JSON object with the extracted information."},
                    {"role": "user", "content": [
                        {"type": "text", "text": msg},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]}
                ],
                temperature=self.temperature
            )
            response = completion.choices[0].message.content
            print('VLM response:', response)
            
            # Try to parse as JSON, if not possible, wrap in JSON
            try:
                # Try to parse the response as JSON first
                parsed_response = json.loads(response)
                return json.dumps(parsed_response)
            except json.JSONDecodeError:
                # If not JSON, wrap the response in a JSON structure
                return json.dumps({"privacy_details": response, "raw_response": response})
                
        except openai.APIConnectionError as e:
            print(f"API error: {e}")
            return json.dumps({"privacy_details": "API error", "error": str(e)})
        except openai.RateLimitError as e:
            print(f"Rate Limit Error: {e}")
            return json.dumps({"privacy_details": "Rate Limit Error", "error": str(e)})
        except openai.APIError as e:
            print(f"API error: {e}")
            return json.dumps({"privacy_details": "API error", "error": str(e)})
        except Exception as e:
            print(f"unknown error: {e}")
            return json.dumps({"privacy_details": "unknown error", "error": str(e)})


def decode_predictions(scores, geometry, conf_threshold=0.5):
    (num_rows, num_cols) = scores.shape[2:4]
    rects = []
    confidences = []

    for y in range(num_rows):
        scores_data = scores[0, 0, y]
        x_data0 = geometry[0, 0, y]
        x_data1 = geometry[0, 1, y]
        x_data2 = geometry[0, 2, y]
        x_data3 = geometry[0, 3, y]
        angles_data = geometry[0, 4, y]

        for x in range(num_cols):
            if scores_data[x] < conf_threshold:
                continue

            offset_x, offset_y = x * 4.0, y * 4.0
            angle = angles_data[x]
            cos = np.cos(angle)
            sin = np.sin(angle)

            h = x_data0[x] + x_data2[x]
            w = x_data1[x] + x_data3[x]

            end_x = int(offset_x + (cos * x_data1[x]) + (sin * x_data2[x]))
            end_y = int(offset_y - (sin * x_data1[x]) + (cos * x_data2[x]))
            start_x = int(end_x - w)
            start_y = int(end_y - h)

            rects.append((start_x, start_y, end_x, end_y))
            confidences.append(float(scores_data[x]))

    return rects, confidences


def east_text_detect_boxes(img_path, num_samples=0, crop_size=320, conf_threshold=0.5, nms_threshold=0.4, sampling_mode='grid'):
    # Use the same EAST model path as in pipeline.py
    east_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frozen_east_text_detection.pb')
    net = cv2.dnn.readNet(east_model_path)

    image = cv2.imread(img_path)
    if image is None:
        return []

    (H, W) = image.shape[:2]

    all_boxes_list = []

    if sampling_mode == 'grid':
        tile = int(crop_size)
        for y0 in range(0, H, tile):
            for x0 in range(0, W, tile):
                actual_w = min(tile, W - x0)
                actual_h = min(tile, H - y0)

                crop = image[y0:y0 + actual_h, x0:x0 + actual_w]
                canvas = np.zeros((tile, tile, 3), dtype=image.dtype)
                canvas[0:actual_h, 0:actual_w] = crop

                blob = cv2.dnn.blobFromImage(
                    canvas, 1.0, (tile, tile), (123.68, 116.78, 103.94), swapRB=True, crop=False
                )

                net.setInput(blob)
                (scores, geometry) = net.forward([
                    "feature_fusion/Conv_7/Sigmoid",
                    "feature_fusion/concat_3",
                ])

                rects, confidences = decode_predictions(scores, geometry, conf_threshold)
                boxes = cv2.dnn.NMSBoxes(rects, confidences, conf_threshold, nms_threshold)

                if len(boxes) > 0:
                    for i in boxes.flatten():
                        (sx, sy, ex, ey) = rects[i]

                        if sx >= actual_w or sy >= actual_h:
                            continue
                        sx = max(0, min(actual_w - 1, sx))
                        ex = max(0, min(actual_w - 1, ex))
                        sy = max(0, min(actual_h - 1, sy))
                        ey = max(0, min(actual_h - 1, ey))

                        start_x = int(sx) + x0
                        start_y = int(sy) + y0
                        end_x = int(ex) + x0
                        end_y = int(ey) + y0

                        start_x = max(0, min(W - 1, start_x))
                        end_x = max(0, min(W - 1, end_x))
                        start_y = max(0, min(H - 1, start_y))
                        end_y = max(0, min(H - 1, end_y))

                        box_list = [start_x, start_y, end_x, start_y, start_x, end_y, end_x, end_y]
                        all_boxes_list.append(box_list)
    else:
        # Fallback to whole-image 320x320 single pass
        newW, newH = (320, 320)
        rW = W / float(newW)
        rH = H / float(newH)
        resized = cv2.resize(image, (newW, newH))
        blob = cv2.dnn.blobFromImage(resized, 1.0, (newW, newH), (123.68, 116.78, 103.94), swapRB=True, crop=False)
        net.setInput(blob)
        (scores, geometry) = net.forward([
            "feature_fusion/Conv_7/Sigmoid",
            "feature_fusion/concat_3",
        ])
        rects, confidences = decode_predictions(scores, geometry, conf_threshold)
        boxes = cv2.dnn.NMSBoxes(rects, confidences, conf_threshold, nms_threshold)
        if len(boxes) > 0:
            for i in boxes.flatten():
                (sx, sy, ex, ey) = rects[i]
                startX = int(sx * rW)
                startY = int(sy * rH)
                endX = int(ex * rW)
                endY = int(ey * rH)
                startX = max(0, min(W - 1, startX))
                endX = max(0, min(W - 1, endX))
                startY = max(0, min(H - 1, startY))
                endY = max(0, min(H - 1, endY))
                all_boxes_list.append([startX, startY, endX, startY, startX, endY, endX, endY])

    return all_boxes_list


def extract_text_from_boxes(image_path, boxes):
    image = cv2.imread(image_path)
    if image is None:
        return ""

    texts = []
    for box in boxes:
        coords = np.array(box, dtype=np.int32).reshape(-1, 2)
        xs = coords[:, 0]
        ys = coords[:, 1]
        x_min, x_max = np.clip(np.min(xs), 0, image.shape[1]-1), np.clip(np.max(xs), 0, image.shape[1]-1)
        y_min, y_max = np.clip(np.min(ys), 0, image.shape[0]-1), np.clip(np.max(ys), 0, image.shape[0]-1)
        roi = image[y_min:y_max+1, x_min:x_max+1]
        if roi.size <= 0:
            continue
        try:
            text = ts.image_to_string(roi, lang='eng+chi_sim').strip()
            if text:
                texts.append(text)
        except Exception:
            continue

    # Concatenate all segments as a single transcript for CER computation
    return "\n".join(texts)


def character_error_rate(ref_list, hyp_list):
    """
    Compute Character Error Rate (CER) between two lists of strings.
    CER = (S + D + I) / N
    where:
        S = # of substitutions
        D = # of deletions
        I = # of insertions
        N = # of characters in reference (ground truth)
    Args:
        ref_list (list of str): Reference (ground truth) string segments
        hyp_list (list of str): Hypothesis (recognized) string segments
    Returns:
        float: CER value (0.0~1.0)
    """
    # Concatenate all segments and remove whitespace
    def normalize(slist):
        return re.sub(r"\s+", "", "".join(slist if slist is not None else []))
    ref = normalize(ref_list)
    hyp = normalize(hyp_list)
    n = len(ref)
    m = len(hyp)
    if n == 0:
        return 0.0 if m == 0 else 1.0

    # DP for Levenshtein distance
    dp = np.zeros((n + 1, m + 1), dtype=np.int32)
    for i in range(n + 1):
        dp[i, 0] = i
    for j in range(m + 1):
        dp[0, j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i, j] = min(
                dp[i - 1, j] + 1,      # deletion
                dp[i, j - 1] + 1,      # insertion
                dp[i - 1, j - 1] + cost  # substitution
            )
    cer = dp[n, m] / float(n)
    if cer>1:
        cer = dp[n, m] / float(max(n,m))
    return float(cer)


def find_positive_images(root_dir, compare_mode='blur'):
    tasks = []
    if not os.path.isdir(root_dir):
        return tasks
    for sub in os.listdir(root_dir):
        sub_dir = os.path.join(root_dir, sub)
        if not os.path.isdir(sub_dir):
            continue
        pos_dir = os.path.join(sub_dir, 'positive')
        if not os.path.isdir(pos_dir):
            continue
        for fn in os.listdir(pos_dir):
            # if not fn.lower().endswith('.jpg'):
            #     continue
            img_name = os.path.splitext(fn)[0]
            orig_path = os.path.join(pos_dir, fn)
            if compare_mode == 'blur':
                comp_path = os.path.join(sub_dir, 'temp', f"{img_name}_compressed_blur_elastic.jpg")
            elif compare_mode == 'compress':
                comp_path = os.path.join(sub_dir, 'temp', f"{img_name}_compressed.jpg")
            elif compare_mode =='ideal':
                comp_path = os.path.join(sub_dir, 'temp', f"{img_name}_blur_elastic_compressed.jpg")
            tasks.append((sub, img_name, orig_path, comp_path))
    return tasks


def compare_privacy_details(original_details, compressed_details):
    """
    Compare privacy details extracted from original and compressed images
    Args:
        original_details (str): JSON string with privacy details from original image
        compressed_details (str): JSON string with privacy details from compressed image
    Returns:
        tuple: (is_consistent, category) where:
            - is_consistent: bool indicating if details match
            - category: str indicating the comparison category ('consistent', 'inconsistent', 'no_privacy')
    """
    try:
        # Parse JSON responses
        orig_data = json.loads(original_details) if isinstance(original_details, str) else original_details
        comp_data = json.loads(compressed_details) if isinstance(compressed_details, str) else compressed_details
        
        # Extract privacy details from both responses
        orig_privacy = orig_data.get('privacy_details', '')
        comp_privacy = comp_data.get('privacy_details', '')
        
        # Check if both responses indicate no privacy information
        orig_no_privacy = 'no privacy information' in orig_privacy.lower()
        comp_no_privacy = 'no privacy information' in comp_privacy.lower()
        
        if orig_no_privacy and comp_no_privacy:
            return True, 'no_privacy'
        
        # If one has privacy info and the other doesn't, they don't match
        if orig_no_privacy != comp_no_privacy:
            return False, 'inconsistent'
        
        # If both have privacy information, compare the content
        # Normalize the text for comparison (remove extra spaces, convert to lowercase)
        orig_normalized = re.sub(r'\s+', ' ', orig_privacy.lower().strip())
        comp_normalized = re.sub(r'\s+', ' ', comp_privacy.lower().strip())
        
        # Check if the normalized content is similar (allowing for some differences in formatting)
        if orig_normalized == comp_normalized:
            return True, 'consistent'
        
        # Additional check: extract specific patterns (phone numbers, emails, etc.) and compare
        orig_patterns = extract_privacy_patterns(orig_privacy)
        comp_patterns = extract_privacy_patterns(comp_privacy)
        
        if orig_patterns == comp_patterns:
            return True, 'consistent'
        
        return False, 'inconsistent'
        
    except Exception as e:
        print(f"Error comparing privacy details: {e}")
        return False, 'error'


def extract_privacy_patterns(text):
    """
    Extract specific privacy patterns from text for comparison
    Args:
        text (str): Text containing privacy information
    Returns:
        dict: Dictionary of extracted patterns
    """
    patterns = {}
    
    # Phone number patterns
    phone_pattern = r'(?:\+?86[-\s]?)?1[3-9]\d{9}|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
    phone_matches = re.findall(phone_pattern, text)
    if phone_matches:
        patterns['phone_numbers'] = sorted(phone_matches)
    
    # Email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        patterns['emails'] = sorted(email_matches)
    
    # ID card patterns
    id_pattern = r'\b\d{15}|\d{18}|\d{17}[Xx]\b'
    id_matches = re.findall(id_pattern, text)
    if id_matches:
        patterns['id_numbers'] = sorted(id_matches)
    
    # Bank card patterns
    bank_pattern = r'\b\d{16,19}\b'
    bank_matches = re.findall(bank_pattern, text)
    if bank_matches:
        patterns['bank_cards'] = sorted(bank_matches)
    
    return patterns


def run_privacy_consistency_analysis(data_dir, output_excel_path, compare_mode='blur'):
    """
    Run privacy consistency analysis using GPT-4o VLM model
    Args:
        data_dir (str): Root directory containing subdirectories with positive and temp folders
        output_excel_path (str): Path to save the results Excel file
    """
    print("Starting privacy consistency analysis with GPT-4o VLM...")
    
    # Initialize GPT model
    gpt = GPTAzure("gpt-4o")
    
    rows = []
    tasks = find_positive_images(data_dir, compare_mode=compare_mode)
    
    print(f"Found {len(tasks)} image pairs to analyze")
    
    for i, (sub, img_name, orig_path, comp_path) in enumerate(tasks):
        print(f"\nProcessing {i+1}/{len(tasks)}: {img_name} in dataset {sub}")
        
        # Extract privacy details from original image
        print("  Analyzing original image...")
        orig_result = gpt.extract_privacy_details(orig_path)
        orig_data = json.loads(orig_result) if isinstance(orig_result, str) else orig_result
        print('orig_data:',orig_data)
        # Extract privacy details from compressed image
        print("  Analyzing compressed image...")
        comp_result = gpt.extract_privacy_details(comp_path)
        comp_data = json.loads(comp_result) if isinstance(comp_result, str) else comp_result
        print('comp_data:',comp_data)
        # Compare the results
        is_consistent, category = compare_privacy_details(orig_result, comp_result)
        
        # Store results
        rows.append({
            'sub_dir': sub,
            'img_name': img_name,
            'original_path': orig_path,
            'compressed_path': comp_path,
            'original_privacy_details': orig_data.get('privacy_details', ''),
            'compressed_privacy_details': comp_data.get('privacy_details', ''),
            'is_consistent': is_consistent,
            'category': category,
            'original_error': orig_data.get('error', ''),
            'compressed_error': comp_data.get('error', '')
        })
        
        print(f"  Result: {'Consistent' if is_consistent else 'Inconsistent'} ({category})")
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    if len(df) == 0:
        print("No data to analyze")
        return
    
    # Calculate accuracy (excluding 'no_privacy' category)
    total_pairs = len(df)
    no_privacy_pairs = len(df[df['category'] == 'no_privacy'])
    valid_pairs = len(df[df['category'] != 'no_privacy'])
    consistent_pairs = len(df[df['is_consistent'] == True])
    valid_consistent_pairs = len(df[(df['is_consistent'] == True) & (df['category'] != 'no_privacy')])
    
    # Calculate accuracy only for valid pairs (excluding no_privacy)
    accuracy = valid_consistent_pairs / valid_pairs if valid_pairs > 0 else 0
    
    # Create summary
    summary_df = pd.DataFrame([
        ['Total Image Pairs', total_pairs],
        ['No Privacy Pairs (excluded from accuracy)', no_privacy_pairs],
        ['Valid Pairs (for accuracy calculation)', valid_pairs],
        ['Consistent Pairs (total)', consistent_pairs],
        ['Valid Consistent Pairs', valid_consistent_pairs],
        ['Inconsistent Pairs', valid_pairs - valid_consistent_pairs],
        ['Accuracy (valid pairs only)', f"{accuracy:.4f}"],
        ['Method', 'GPT-4o VLM Privacy Consistency Analysis']
    ], columns=['Metric', 'Value'])
    
    # Save to Excel
    out_dir = os.path.dirname(output_excel_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    
    try:
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Detailed Results', index=False)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"\n=== PRIVACY CONSISTENCY ANALYSIS RESULTS ===")
        print(f"Total Image Pairs: {total_pairs}")
        print(f"No Privacy Pairs (excluded from accuracy): {no_privacy_pairs}")
        print(f"Valid Pairs (for accuracy calculation): {valid_pairs}")
        print(f"Valid Consistent Pairs: {valid_consistent_pairs}")
        print(f"Valid Inconsistent Pairs: {valid_pairs - valid_consistent_pairs}")
        print(f"Accuracy (valid pairs only): {accuracy:.4f}")
        print(f"Results saved to: {output_excel_path}")
        
    except Exception as e:
        print(f"Error saving Excel: {e}")


def run_character_leakage_rate(data_dir, output_excel_path, compare_mode='blur'):
    rows = []
    tasks = find_positive_images(data_dir, compare_mode=compare_mode)

    for sub, img_name, orig_path, comp_path in tasks:
        # Original image OCR
        print(f'{img_name} in dataset {sub} starts...')
        orig_boxes = east_text_detect_boxes(orig_path, sampling_mode='grid')
        orig_text = extract_text_from_boxes(orig_path, orig_boxes)

        # Compressed image OCR (if exists)
        if os.path.isfile(comp_path):
            # print(f"comp_path:{comp_path}")
            comp_boxes = east_text_detect_boxes(comp_path, sampling_mode='grid')
            comp_text = extract_text_from_boxes(comp_path, comp_boxes)
        else:
            print(f'the {comp_path} does not exist!')
            comp_path = os.path.join(data_dir, sub, 'positive_ideal', f"{img_name}_blur_elastic.jpg")
            if os.path.isfile(comp_path):
                comp_boxes = east_text_detect_boxes(comp_path, sampling_mode='grid')
                comp_text = extract_text_from_boxes(comp_path, comp_boxes)
            else:
                comp_boxes = []
                comp_text = ""

        cer = character_error_rate(orig_text, comp_text)

        rows.append({
            'sub_dir': sub,
            'img_name': img_name,
            'original_path': orig_path,
            'compressed_path': comp_path if os.path.isfile(comp_path) else '',
            'orig_text_len': len(orig_text),
            'comp_text_len': len(comp_text),
            'cer': cer
        })

    df = pd.DataFrame(rows)
    if len(df) == 0:
        # Create empty summary to avoid writer errors
        summary_df = pd.DataFrame([
            ['Count', 0],
            ['Mean CER', 'nan'],
            ['Std CER', 'nan']
        ], columns=['Metric', 'Value'])
    else:
        mean_cer = float(df['cer'].mean())
        std_cer = float(df['cer'].std(ddof=0)) if len(df) > 1 else 0.0
        summary_df = pd.DataFrame([
            ['Count', len(df)],
            ['Mean CER', f"{mean_cer:.6f}"],
            ['Std CER', f"{std_cer:.6f}"]
        ], columns=['Metric', 'Value'])

    # Save to Excel
    out_dir = os.path.dirname(output_excel_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Detailed', index=False)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
    except Exception as e:
        print(f"Error saving Excel: {e}")


if __name__ == '__main__':
    # Example usage (adjust paths as needed):
    data_dir = 'Dataset'
    orig_path='data.png'
    comp_path='data.jpg'
    
    # Choose which analysis to run:
    analysis_mode = 'single'  # 'privacy_consistency' or 'CER'
    '''
    privacy_consistency: Runs VLM on each original/processed image pair to compare extracted privacy details and measure semantic leakage across the dataset.
    CER: Runs EAST text detection and Tesseract OCR on each original/processed image pair to compute Character Error Rate, measuring how much raw text survives obfuscation.
    Single: Sends a single pair of images to GPT-4o to quickly verify credentials and test the privacy comparison logic on two specific images.
    '''
    compare_mode='blur'
    if analysis_mode == 'privacy_consistency':
        # Run privacy consistency analysis with GPT-4o VLM
        output_excel = os.path.join(data_dir, 'Privacy_Consistency_ideal.xlsx')
        run_privacy_consistency_analysis(data_dir, output_excel, compare_mode=compare_mode)
    elif analysis_mode=='CER':
        # Run character leakage rate analysis (original functionality)
        output_excel = os.path.join(data_dir, 'CER_ideal.xlsx')
        run_character_leakage_rate(data_dir, output_excel, compare_mode=compare_mode)

    else:
        gpt = GPTAzure("gpt-4o")
        print("  Analyzing original image...")
        orig_result = gpt.extract_privacy_details(orig_path)
        orig_data = json.loads(orig_result) if isinstance(orig_result, str) else orig_result
        print('orig_data:',orig_data)
        # Extract privacy details from compressed image
        print("  Analyzing compressed image...")
        comp_result = gpt.extract_privacy_details(comp_path)
        comp_data = json.loads(comp_result) if isinstance(comp_result, str) else comp_result
        print('comp_data:',comp_data)
        # Compare the results
        is_consistent, category = compare_privacy_details(orig_result, comp_result)
        print('is_consistent:',is_consistent)
        print('category:',category)




