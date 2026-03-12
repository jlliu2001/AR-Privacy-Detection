using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.Networking;
using TMPro;
using System.Net;
using System.Net.Sockets;
using Newtonsoft.Json;
#if UNITY_ANDROID
using UnityEngine.Android;
#endif

public enum WarningUIMode
{
    CenterPanel,    // 原始方式：屏幕中央红色panel
    TopText,        // 方式1：屏幕上方警示文字
    BoxHighlight    // 方式2：矩形区域高亮
}

public class ARPrivacyMonitorHttp : MonoBehaviour
{
    public float captureInterval = 5f; // 截图间隔（秒）
    public string serverUrl = "http://127.0.0.1:5000/check_privacy"; // PC端服务器地址
    public string pcServerIp = "192.168.251.57"; // PC端IP，Inspector可配置
    public string screenshotsFolder = "CapturedImages";
    
    [Header("Image Compression Settings")]
    public int targetWidth = 0; // 目标宽度，0表示不缩放
    public int targetHeight = 0; // 目标高度，0表示不缩放
    [Range(10, 100)]
    public int jpegQuality = 75; // JPEG质量 (10-100)
    public bool useJPEG = true; // 使用JPEG格式而非PNG
    
    [Header("Warning UI Settings")]
    public WarningUIMode warningMode = WarningUIMode.CenterPanel; // 警告UI模式
    public GameObject warningPanel; // 警告弹窗Panel（中央模式）
    public TMP_Text warningText; // 警告文本（中央模式）
    public TMP_Text topWarningText; // 顶部警告文本（顶部模式）
    public Transform boxHighlightParent; // 矩形高亮父物体（矩形模式）
    public GameObject boxHighlightPrefab; // 矩形高亮预制体
    public TMP_Text debugText; // 用于移动端调试信息显示

    private float timer = 0f;
    private string lastScreenshotPath = "";
    private List<GameObject> activeBoxHighlights = new List<GameObject>();
    private Coroutine blinkingCoroutine;
    private Coroutine centerPanelBlinkCoroutine;
    private Coroutine topTextBlinkCoroutine;

    void Start()
    {
        // 自动设置 serverUrl（仅在移动端）
#if UNITY_ANDROID || UNITY_IOS
        // 这里假设 pcServerIp 已在 Inspector 设置为 PC 的局域网IP
        serverUrl = $"http://{pcServerIp}:5000/check_privacy";
#endif
        if (warningPanel != null)
            warningPanel.SetActive(false);
        if (topWarningText != null)
            topWarningText.gameObject.SetActive(false);
        ClearBoxHighlights();
        if (!File.Exists(Path.Combine(Application.persistentDataPath, screenshotsFolder)))
        {
            ShowDebug("screenshotsFolder not exists, create it: " + screenshotsFolder);
            Directory.CreateDirectory(Path.Combine(Application.persistentDataPath, screenshotsFolder));
        }
        ShowDebug("Start: serverUrl=" + serverUrl);
#if UNITY_ANDROID
        
        if (!Permission.HasUserAuthorizedPermission(Permission.ExternalStorageWrite))
        {
            Permission.RequestUserPermission(Permission.ExternalStorageWrite);
            ShowDebug("Requesting WRITE_EXTERNAL_STORAGE permission...");
        }
#endif
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= captureInterval)
        {
            timer = 0f;
            ShowDebug("Start...");
            StartCoroutine(CaptureAndSend());
        }
    }

    IEnumerator CaptureAndSend()
    {
        // string screenshotPath = Path.Combine(Application.persistentDataPath, screenshotsFolder, "frame"  + ".png");
        // ScreenCapture.CaptureScreenshot(screenshotPath);
        // lastScreenshotPath = screenshotPath;
        // ShowDebug("screencapture..." + screenshotPath);
        // yield return new WaitForSeconds(0.5f); // 等待截图写入
        // if (File.Exists(screenshotPath))
        // {
        //     UnityEngine.Debug.Log("screencapture!");
        //     UnityEngine.Debug.Log("screenshotPath: " + screenshotPath);
        //     // warningText.text = "screencapture!";
        //     ShowDebug("screencapture success: " + screenshotPath);
        // }
        // else
        // {
        //     UnityEngine.Debug.Log("screenshotPath not exists!");
        //     // warningText.text = "no screencapture!";
        //     ShowDebug("screencapture failed: " + screenshotPath);
        // }
        // yield return StartCoroutine(UploadImage(screenshotPath));

        // yield return new WaitForEndOfFrame();
        
        // 确定文件扩展名
        string fileExtension = useJPEG ? ".jpg" : ".png";
        string screenshotPath = Path.Combine(Application.persistentDataPath, screenshotsFolder, "frame" + fileExtension);
        ShowDebug($"before Texture2D");
        // 创建原始截图纹理
        Texture2D originalTex = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
        originalTex.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
        originalTex.Apply();
        
        // 计算压缩后的尺寸
        int finalWidth = Screen.width;
        int finalHeight = Screen.height;
        // ShowDebug("Screen.width:" + Screen.width + " Screen.height:" + Screen.height);
        
        if (targetWidth > 0 && targetHeight > 0)
        {
            // 保持宽高比缩放
            float aspectRatio = (float)Screen.width / Screen.height;
            if (Screen.width > targetWidth || Screen.height > targetHeight)
            {
                if (aspectRatio > (float)targetWidth / targetHeight)
                {
                    finalWidth = targetWidth;
                    finalHeight = Mathf.RoundToInt(targetWidth / aspectRatio);
                }
                else
                {
                    finalHeight = targetHeight;
                    finalWidth = Mathf.RoundToInt(targetHeight * aspectRatio);
                }
            }
        }
        
        // 如果需要缩放，创建缩放后的纹理
        Texture2D finalTex = originalTex;
        if (finalWidth != Screen.width || finalHeight != Screen.height)
        {
            finalTex = ResizeTexture(originalTex, finalWidth, finalHeight);
            Destroy(originalTex);
        }
        
        // 根据格式编码
        byte[] bytes;
        if (useJPEG)
        {
            bytes = finalTex.EncodeToJPG(jpegQuality);
        }
        else
        {
            bytes = finalTex.EncodeToPNG();
        }
        
        File.WriteAllBytes(screenshotPath, bytes);
        Destroy(finalTex);
        
        ShowDebug($"Image compressed: {Screen.width}x{Screen.height} -> {finalWidth}x{finalHeight}, Size: {bytes.Length / 1024}KB");
        Debug.Log($"Image compressed: {Screen.width}x{Screen.height} -> {finalWidth}x{finalHeight}, Size: {bytes.Length / 1024}KB");
        lastScreenshotPath = screenshotPath;
        // ShowDebug("screencapture..." + screenshotPath);
        Debug.Log("screencapture..." + screenshotPath);
        
        if (File.Exists(screenshotPath))
        {
            // ShowDebug("screencapture success: " + screenshotPath);
            Debug.Log("screencapture success: " + screenshotPath);
        }
        else
        {
            // ShowDebug("screencapture failed: " + screenshotPath);
            Debug.Log("screencapture failed: " + screenshotPath);
        }
        yield return StartCoroutine(UploadImage(screenshotPath));
        // yield return StartCoroutine(UploadImage_test(screenshotPath));
    }

    // 纹理缩放方法
    Texture2D ResizeTexture(Texture2D originalTexture, int targetWidth, int targetHeight)
    {
        RenderTexture renderTexture = RenderTexture.GetTemporary(targetWidth, targetHeight);
        RenderTexture.active = renderTexture;
        
        Graphics.Blit(originalTexture, renderTexture);
        
        Texture2D resizedTexture = new Texture2D(targetWidth, targetHeight, TextureFormat.RGB24, false);
        resizedTexture.ReadPixels(new Rect(0, 0, targetWidth, targetHeight), 0, 0);
        resizedTexture.Apply();
        
        RenderTexture.active = null;
        RenderTexture.ReleaseTemporary(renderTexture);
        
        return resizedTexture;
    }

    IEnumerator UploadImage(string imagePath)
    {
        // 实际手机屏幕是数字从小到大对应图像从下向上，因此回来的Box可能需要做一个倒置处理
        byte[] imageData = File.ReadAllBytes(imagePath);
        WWWForm form = new WWWForm();
        string mimeType = imagePath.EndsWith(".jpg") || imagePath.EndsWith(".jpeg") ? "image/jpeg" : "image/png";
        form.AddBinaryData("image", imageData, Path.GetFileName(imagePath), mimeType);
        Debug.Log("imagePath: " + imagePath);
        if (warningText != null)
            warningText.text = "loading...";
        ShowDebug("uploading... serverUrl=" + serverUrl);
        using (UnityWebRequest www = UnityWebRequest.Post(serverUrl, form))
        {
            Debug.Log("loading...");
            ShowDebug("loading...");
            yield return www.SendWebRequest();
            Debug.Log("www.result: " + www.result);
            Debug.Log("serverUrl: " + serverUrl);
            ShowDebug("uploading success: " + www.result + ", error: " + www.error);
            if (www.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError("HTTP Error: " + www.error);
                ShowDebug("HTTP error: " + www.error);
                HideWarningUI();
                yield break;
            }
            string result = www.downloadHandler.text;
            bool isPrivacy = false;
            PrivacyResult json = null;
            try
            {
                json = JsonConvert.DeserializeObject<PrivacyResult>(result);
                isPrivacy = json.privacy;
                Debug.Log("isPrivacy: " + isPrivacy);
                ShowDebug("isPrivacy: " + isPrivacy);
            }
            catch
            {
                Debug.LogError("parse server return failed: " + result);
                ShowDebug("parse server return failed: " + result);
            }
            if (isPrivacy && json != null)
            {
                
                ShowWarningUI(json.box_list);
            }
            else
            {
                HideWarningUI();
            }
        }
    }



    IEnumerator UploadImage_test(string imagePath)
    {
        // byte[] imageData = File.ReadAllBytes(imagePath);
        // WWWForm form = new WWWForm();
        // string mimeType = imagePath.EndsWith(".jpg") || imagePath.EndsWith(".jpeg") ? "image/jpeg" : "image/png";
        // form.AddBinaryData("image", imageData, Path.GetFileName(imagePath), mimeType);
        // Debug.Log("imagePath: " + imagePath);
        // if (warningText != null)
        //     warningText.text = "loading...";
        // ShowDebug("uploading... serverUrl=" + serverUrl);
        // using (UnityWebRequest www = UnityWebRequest.Post(serverUrl, form))
        // {
        //     Debug.Log("loading...");
        //     ShowDebug("loading...");
        //     yield return www.SendWebRequest();
        //     Debug.Log("www.result: " + www.result);
        //     Debug.Log("serverUrl: " + serverUrl);
        //     ShowDebug("uploading success: " + www.result + ", error: " + www.error);
        //     if (www.result != UnityWebRequest.Result.Success)
        //     {
        //         Debug.LogError("HTTP Error: " + www.error);
        //         ShowDebug("HTTP error: " + www.error);
        //         HideWarningUI();
        //         yield break;
        //     }
        //     string result = www.downloadHandler.text;
        // ,[0.3, 0.3, 0.6, 0.3, 0.3, 0.6, 0.6, 0.6]
        string result = @"{""privacy"":true, ""box_list"":[[0.2, 0.2, 0.3, 0.2, 0.2, 0.3, 0.3, 0.3]]}";
        bool isPrivacy = false;
        PrivacyResult json = null;
        try
        {
            // json = JsonUtility.FromJson<PrivacyResult>(result);
            json = JsonConvert.DeserializeObject<PrivacyResult>(result);
            isPrivacy = json.privacy;
            Debug.Log("isPrivacy: " + isPrivacy);
            // ShowDebug("server return: " + result);
        }
        catch
        {
            Debug.LogError("parse server return failed: " + result);
            // ShowDebug("parse server return failed: " + result);
        }
        if (isPrivacy && json != null)
        {
            // Debug.Log("json.box_list:" + json.box_list);
            if (json.box_list == null)
            {
                Debug.Log("box_list为null");
            }
            else if (json.box_list.Length == 0)
            {
                Debug.Log("box_list为空数组");
            }
            else{
                // Debug.Log("box_list长度: " + json.box_list.Length);
                ShowWarningUI(json.box_list);
            }
            
        }
        else
        {
            HideWarningUI();
        }
        yield return null;
        // }
    }

    void ShowWarningUI(float[][] boxList = null)
    {
        switch (warningMode)
        {
            case WarningUIMode.CenterPanel:
                ShowCenterPanelWarning();
                break;
                
            case WarningUIMode.TopText:
                ShowTopTextWarning();
                break;
                
            case WarningUIMode.BoxHighlight:
                ShowBoxHighlightWarning(boxList);
                break;
        }
    }
    
    void ShowCenterPanelWarning()
    {
        if (warningPanel != null && warningText != null)
        {
            warningText.text = "PRIVACY WARNING!";
            warningPanel.SetActive(true);
            Color warningColor = new Color(1f, 0.2f, 0.2f, 0.9f);
            warningPanel.GetComponent<Image>().color = warningColor;
            Debug.LogWarning("The screen contains a risk of privacy leakage!");
            
            if (centerPanelBlinkCoroutine != null)
                StopCoroutine(centerPanelBlinkCoroutine);
            centerPanelBlinkCoroutine = StartCoroutine(BlinkCenterPanel());
        }
    }
    
    void ShowTopTextWarning()
    {
        if (topWarningText != null)
        {
            topWarningText.text = "PRIVACY WARNING!";
            topWarningText.color = Color.red;
            topWarningText.gameObject.SetActive(true);
            Debug.LogWarning("The screen contains a risk of privacy leakage!");
            
            if (topTextBlinkCoroutine != null)
                StopCoroutine(topTextBlinkCoroutine);
            topTextBlinkCoroutine = StartCoroutine(BlinkTopText());
        }
    }
    
    void ShowBoxHighlightWarning(float[][] boxList)
    {
        // 先停止之前的闪烁协程
        if (blinkingCoroutine != null)
        {
            StopCoroutine(blinkingCoroutine);
            blinkingCoroutine = null;
        }
        
        ClearBoxHighlights();
        // Debug.Log("boxlist:" + boxList);
        // Debug.Log("boxHighlightPrefab:" + boxHighlightPrefab);
        // Debug.Log("boxHighlightParent:" + boxHighlightParent);
        if (boxList != null && boxHighlightPrefab != null && boxHighlightParent != null)
        {
            foreach (float[] box in boxList)
            {
                Debug.Log("boxlist:" + box);
                if (box.Length >= 8)
                {
                    Debug.Log("CreateBoxHighlight boxlist:" + box);
                    CreateBoxHighlight(box);
                }
            }
            
            // 重新启动闪烁协程
            blinkingCoroutine = StartCoroutine(BlinkBoxHighlights());
        }
        Debug.LogWarning("[BoxHighlight]The screen contains a risk of privacy leakage!");
    }

    void HideWarningUI()
    {
        if (warningPanel != null)
            warningPanel.SetActive(false);
        if (topWarningText != null)
            topWarningText.gameObject.SetActive(false);
        ClearBoxHighlights();
        
        if (blinkingCoroutine != null)
        {
            StopCoroutine(blinkingCoroutine);
            blinkingCoroutine = null;
        }
        if (centerPanelBlinkCoroutine != null)
        {
            StopCoroutine(centerPanelBlinkCoroutine);
            centerPanelBlinkCoroutine = null;
        }
        if (topTextBlinkCoroutine != null)
        {
            StopCoroutine(topTextBlinkCoroutine);
            topTextBlinkCoroutine = null;
        }
    }

    void ShowDebug(string msg)
    {
        if (debugText != null)
        {
            debugText.text = msg;
            //  + "\n" + debugText.text
        }
    }

    [System.Serializable]
    public class PrivacyResult
    {
        public bool privacy;
        public float[][] box_list;
    }
    void CreateBoxHighlight(float[] box)
    {
        GameObject highlight = Instantiate(boxHighlightPrefab, boxHighlightParent);
        RectTransform rectTransform = highlight.GetComponent<RectTransform>();
        
        float startX = box[0] * Screen.width;
        float startY = box[1] * Screen.height;
        float endX = box[2] * Screen.width;
        float endY = box[5] * Screen.height;
        
        // Debug.Log("Screen.width:" + Screen.width);
        // Debug.Log("Screen.width:" + Screen.height);
        
        
        float width = Mathf.Abs(endX - startX);
        float height = Mathf.Abs(endY - startY);
        float centerX = (startX + endX) / 2;
        float centerY = Screen.height - (startY + endY) / 2;
        ShowDebug("width: " + width + "height:"+ height);
        
        rectTransform.anchoredPosition = new Vector2(centerX - Screen.width / 2, centerY - Screen.height / 2);
        rectTransform.sizeDelta = new Vector2(width, height);
        
        Image image = highlight.GetComponent<Image>();
        if (image != null)
        {
            // Debug.Log("image:" + image);
            image.color = new Color(1f, 0f, 0f, 0.4f);
        }
        
        // TMP_Text text = highlight.GetComponentInChildren<TMP_Text>();
        // if (text != null)
        // {
        //     // Debug.Log("text:" + text);
        //     text.text = "Privacy Warning";
        //     text.color = Color.green;
        // }
        // highlight
        Debug.Log($"Created highlight at: pos({startX}, {startY}), size({width}, {height})");
        
        Debug.Log("rectTransform.anchoredPosition:" + highlight.GetComponent<RectTransform>().anchoredPosition);
        // Debug.Log("text.text:" + highlight.GetComponentInChildren<TMP_Text>().text);
        
        activeBoxHighlights.Add(highlight);
    }
    
    void ClearBoxHighlights()
    {
        foreach (GameObject highlight in activeBoxHighlights)
        {
            if (highlight != null)
                Destroy(highlight);
        }
        activeBoxHighlights.Clear();
    }
    
    IEnumerator BlinkCenterPanel()
    {
        float duration = 6f;
        float blinkInterval = 1f;
        float elapsed = 0f;
        
        while (elapsed < duration && warningPanel != null)
        {
            warningPanel.SetActive(!warningPanel.activeInHierarchy);
            yield return new WaitForSeconds(blinkInterval);
            elapsed += blinkInterval;
        }
        
        if (warningPanel != null)
            warningPanel.SetActive(false);
        centerPanelBlinkCoroutine = null;
    }
    
    IEnumerator BlinkTopText()
    {
        float duration = 6f;
        float blinkInterval = 1f;
        float elapsed = 0f;
        
        while (elapsed < duration && topWarningText != null)
        {
            topWarningText.gameObject.SetActive(!topWarningText.gameObject.activeInHierarchy);
            yield return new WaitForSeconds(blinkInterval);
            elapsed += blinkInterval;
        }
        
        if (topWarningText != null)
            topWarningText.gameObject.SetActive(false);
        topTextBlinkCoroutine = null;
    }
    
    IEnumerator BlinkBoxHighlights()
    {
        float duration = 6f;
        float blinkInterval = 1f;
        float elapsed = 0f;
        
        while (elapsed < duration && activeBoxHighlights.Count > 0)
        {
            // 创建副本以避免在迭代过程中修改列表
            for (int i = activeBoxHighlights.Count - 1; i >= 0; i--)
            {
                if (i < activeBoxHighlights.Count && activeBoxHighlights[i] != null)
                {
                    activeBoxHighlights[i].SetActive(!activeBoxHighlights[i].activeInHierarchy);
                }
            }
            
            yield return new WaitForSeconds(blinkInterval);
            elapsed += blinkInterval;
        }
        
        ClearBoxHighlights();
        blinkingCoroutine = null;
    }
    
    IEnumerator HideAlertAfterDelay(float delay)
    {
        yield return new WaitForSeconds(delay);
        if (warningPanel != null)
            warningPanel.SetActive(false);
        // UpdateStatusText("监控中...");
    }
} 