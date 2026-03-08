using UnityEngine;
using System.Diagnostics;
using System.IO;
using System.Text;
using Newtonsoft.Json.Linq;



public class SecurityDetection : MonoBehaviour
{
public string pythonExePath = @"python";  
    public string scriptPath = @"./Assets/MobileARTemplateAssets/Scripts/ocr_script.py";  // Python OCR script
    public string screenshotsFolder = "CapturedImages"; 

    private int frameCount = 0;  // frame count
    private const int captureInterval = 50;  // frequency

    void Update()
    {
        
        if (++frameCount % captureInterval == 0)
        {
            CaptureAndProcessImage();
        }
    }

    void CaptureAndProcessImage()
    {
        string screenshotPath = Path.Combine(Application.persistentDataPath, screenshotsFolder, "frame" + Time.frameCount + ".png");

        
        UnityEngine.Debug.Log("screenshotPath:"+screenshotPath);
        Directory.CreateDirectory(Path.Combine(Application.persistentDataPath, screenshotsFolder));

        // using ScreenCapture.CaptureScreenshot and saving the image
        ScreenCapture.CaptureScreenshot(screenshotPath);
        UnityEngine.Debug.Log("screencapture!");

        
        Invoke("RunOCR", 0.5f); // delay for saving
    }

    void RunOCR()
    {
        // get the screenshot path
        string screenshotPath = Path.Combine(Application.persistentDataPath, screenshotsFolder, "frame" + Time.frameCount + ".png");

        // exceed Python OCR script
        ProcessStartInfo start = new ProcessStartInfo();
        start.FileName = pythonExePath;
        start.Arguments = $"\"{scriptPath}\" \"{screenshotPath}\"";
        start.UseShellExecute = false;
        start.RedirectStandardOutput = true;
        start.RedirectStandardError = true;
        start.CreateNoWindow = true;
        start.StandardOutputEncoding = Encoding.UTF8;

        using (Process process = Process.Start(start))
        {
            string result = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit();

            if (!string.IsNullOrEmpty(error))
            {
                UnityEngine.Debug.LogError("Python Error: " + error);
                return;
            }

            JObject json = JObject.Parse(result);
            bool isSensitive = json["sensitive"]?.Value<bool>() ?? false;
            string detectedText = json["text"]?.ToString();

            UnityEngine.Debug.Log("OCR Result: " + detectedText);

            if (isSensitive)
            {
                ShowWarningUI(detectedText);
            }

        }
    }

    void ShowWarningUI(string text)
    {
        // UI warning
        UnityEngine.Debug.LogWarning("⚠️ SENSITIVE INFORMATION DETECTED: " + text);
    }
}
