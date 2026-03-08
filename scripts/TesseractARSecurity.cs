using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using System.IO;
using System.Diagnostics;

public class TesseractARSecurity : MonoBehaviour
{
    [Header("camera setting")]
    public Camera arCamera;
    public int captureInterval = 50; // frequency
    
    [Header("UI")]
    public Text warningText;
    public Text statusText;
    public GameObject warningPanel;
    public Slider confidenceSlider;
    
    [Header("OCR setting")]
    [Range(0.1f, 1.0f)]
    public float confidenceThreshold = 0.6f;
    public string tesseractPath = ""; // Tesseract exe path
    
    private int frameCounter = 0;
    private bool isProcessing = false;
    private string tempImagePath;
    
    // Dictionary
    private Dictionary<string, int> sensitivePatterns = new Dictionary<string, int>
    {
        // high level
        {"passport", 3}, {"social security", 3},
        {"ssn", 3}, {"id card", 3},
        
        // middle level 
        {"credit card", 2}, {"bank card", 2},
        {"account number", 2},
        {"password", 2}, {"pin", 2},
        
        // low level
        {"phone", 1}, {"address", 1}, 
         {"email", 1},
        {"node", 1} 
    };
    
    // RegularExpressions
    private List<System.Text.RegularExpressions.Regex> riskPatterns = new List<System.Text.RegularExpressions.Regex>
    {
        new System.Text.RegularExpressions.Regex(@"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), // credit card
        new System.Text.RegularExpressions.Regex(@"\b\d{3}-\d{2}-\d{4}\b"), // SSN
        new System.Text.RegularExpressions.Regex(@"\b[A-Z]\d{8}\b"), // passport
        new System.Text.RegularExpressions.Regex(@"\b\d{11}\b"), // phone number
        new System.Text.RegularExpressions.Regex(@"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b") // email
    };
    
    void Start()
    {
        InitializeSystem();
    }
    
    void InitializeSystem()
    {
        if (arCamera == null)
            arCamera = Camera.main;
            
        
        tempImagePath = Path.Combine(Application.persistentDataPath, "temp_capture.png");
        
        
        if (string.IsNullOrEmpty(tesseractPath))
        {
            tesseractPath = FindTesseractPath();
        }
        
        warningPanel.SetActive(false);
        UpdateStatusText("init");
        
        
        if (confidenceSlider != null)
        {
            confidenceSlider.value = confidenceThreshold;
            confidenceSlider.onValueChanged.AddListener(OnConfidenceChanged);
        }
    }
    
    void Update()
    {
        frameCounter++;
        
        if (frameCounter >= captureInterval && !isProcessing)
        {
            frameCounter = 0;
            StartCoroutine(CaptureAndAnalyzeCoroutine());
        }
    }
    
    // find the Tesseract OCR path
    string FindTesseractPath()
    {
        string[] possiblePaths = {
            @"E:\TesseractOCR\tesseract.exe",
            @"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        };
        
        foreach (string path in possiblePaths)
        {
            if (File.Exists(path))
            {
                return path;
            }
        }
        
        UnityEngine.Debug.LogWarning("please provide the correct path of OCR");
        return "";
    }
    
    IEnumerator CaptureAndAnalyzeCoroutine()
    {
        isProcessing = true;
        UpdateStatusText("screenshot...");
        

        UnityEngine.Debug.Log("screenshotPath:"+tempImagePath);
        
        ScreenCapture.CaptureScreenshot(tempImagePath);
        UnityEngine.Debug.Log("screencapture!");
        
        UpdateStatusText("recogniting...");
        
        
        
        yield return StartCoroutine(PerformOCR());
        
        
        // DestroyImmediate(screenshot);
        isProcessing = false;
    }
    
    
    IEnumerator PerformOCR()
    {
        UnityEngine.Debug.Log("tesseractPath:"+tesseractPath);
        if (string.IsNullOrEmpty(tesseractPath) || !File.Exists(tesseractPath))
        {
            UpdateStatusText("Tesseract OCR is not installed!");
            UnityEngine.Debug.Log("Tesseract OCR is not installed!");
            yield break;
        }
        
        string outputPath = Path.Combine(Application.persistentDataPath, "ocr_output");
        
        // process Tesseract command
        string arguments = $"\"{tempImagePath}\" \"{outputPath}\" -l eng+chi_sim --psm 6";
        UnityEngine.Debug.Log("arguments:"+arguments);
        ProcessStartInfo startInfo = new ProcessStartInfo
        {
            FileName = tesseractPath,
            Arguments = arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        
        
        string ocrResult = "";
        bool ocrCompleted = false;
        
        System.Threading.Thread ocrThread = new System.Threading.Thread(() =>
        {
            try
            {
                using (Process process = Process.Start(startInfo))
                {
                    process.WaitForExit();
                    
                    string outputFile = outputPath + ".txt";
                    if (File.Exists(outputFile))
                    {
                        ocrResult = File.ReadAllText(outputFile);
                        UnityEngine.Debug.Log("ocrResult:"+ocrResult);
                        File.Delete(outputFile); 
                    }
                }
            }
            catch (Exception e)
            {
                UnityEngine.Debug.LogError("OCR error: " + e.Message);
            }
            finally
            {
                ocrCompleted = true;
            }
        });
        
        ocrThread.Start();
        
        
        while (!ocrCompleted)
        {
            yield return new WaitForSeconds(0.1f);
        }
        
        if (!string.IsNullOrEmpty(ocrResult))
        {
            AnalyzeTextForSecurity(ocrResult);
            
        }
        else
        {
            UpdateStatusText("no word");
            
        }
    }
    
    void AnalyzeTextForSecurity(string detectedText)
    {
        List<SecurityThreat> threats = new List<SecurityThreat>();
        string lowerText = detectedText.ToLower();
        
        // key words
        foreach (var pattern in sensitivePatterns)
        {
            if (lowerText.Contains(pattern.Key.ToLower()))
            {
                threats.Add(new SecurityThreat
                {
                    Type = "word",
                    Content = pattern.Key,
                    RiskLevel = pattern.Value,
                    Confidence = 0.9f
                });
            }
        }
        
        // regular expression
        foreach (var regex in riskPatterns)
        {
            var matches = regex.Matches(detectedText);
            foreach (System.Text.RegularExpressions.Match match in matches)
            {
                threats.Add(new SecurityThreat
                {
                    Type = "regular",
                    Content = MaskSensitiveData(match.Value),
                    RiskLevel = 3,
                    Confidence = 0.95f
                });
            }
        }
        
        // display the warning
        if (threats.Count > 0)
        {
            ShowSecurityAlert(threats);
            UnityEngine.Debug.LogWarning("Alarm!");
        }
        else
        {
            UpdateStatusText("no Alarm");
            UnityEngine.Debug.Log("no Alarm!");
        }
    }
    
    void ShowSecurityAlert(List<SecurityThreat> threats)
    {
        // calculate the warning level
        int maxRiskLevel = 0;
        foreach (var threat in threats)
        {
            if (threat.RiskLevel > maxRiskLevel)
                maxRiskLevel = threat.RiskLevel;
        }
        
        // warning message
        string alertMessage = GetRiskLevelText(maxRiskLevel) + "\n detections:\n\n";
        
        foreach (var threat in threats)
        {
            if (threat.Confidence >= confidenceThreshold)
            {
                alertMessage += $"• {threat.Type}: {threat.Content}\n";
            }
        }
        
        alertMessage += "\n There are some security alert!";
        
        // display the UI
        warningText.text = alertMessage;
        warningPanel.SetActive(true);
        
        // change the color
        Color warningColor = GetRiskColor(maxRiskLevel);
        warningPanel.GetComponent<Image>().color = warningColor;
        
        UpdateStatusText($"found the number of security alert: {threats.Count}");
        
        
        // hide the warning
        StartCoroutine(HideAlertAfterDelay(5.0f));
        
    }
    
    string GetRiskLevelText(int level)
    {
        switch (level)
        {
            case 3: return "🔴 high risk level";
            case 2: return "🟡 middle risk level";
            case 1: return "🟢 low risk level";
            default: return "ℹ️ save";
        }
    }
    
    Color GetRiskColor(int level)
    {
        switch (level)
        {
            case 3: return new Color(1f, 0.2f, 0.2f, 0.9f); // red
            case 2: return new Color(1f, 0.8f, 0.2f, 0.9f); // yellow
            case 1: return new Color(0.2f, 0.8f, 0.2f, 0.9f); // green
            default: return new Color(0.5f, 0.5f, 0.5f, 0.9f); // grey
        }
    }
    
    string MaskSensitiveData(string data)
    {
        if (data.Length <= 4) return "****";
        
        string start = data.Substring(0, 2);
        string end = data.Substring(data.Length - 2);
        string middle = new string('*', data.Length - 4);
        
        return start + middle + end;
    }
    
    IEnumerator HideAlertAfterDelay(float delay)
    {
        yield return new WaitForSeconds(delay);
        warningPanel.SetActive(false);
        UpdateStatusText("Alert...");
    }
    
    void UpdateStatusText(string status)
    {
        if (statusText != null)
        {
            statusText.text = $"status: {status}";
        }
    }
    
    void OnConfidenceChanged(float value)
    {
        confidenceThreshold = value;
    }
    
    
    public void AddSensitivePattern(string pattern, int riskLevel)
    {
        sensitivePatterns[pattern.ToLower()] = riskLevel;
    }
    
    public void RemoveSensitivePattern(string pattern)
    {
        sensitivePatterns.Remove(pattern.ToLower());
    }
    
    void OnDestroy()
    {
        // remove the temp files
        if (File.Exists(tempImagePath))
        {
            File.Delete(tempImagePath);
        }
    }
}

[System.Serializable]
public class SecurityThreat
{
    public string Type;      // warning type
    public string Content;   // warning content
    public int RiskLevel;    // 1-3
    public float Confidence; 
}
