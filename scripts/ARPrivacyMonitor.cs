using System.Collections;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using UnityEngine.UI;

public class ARPrivacyMonitor : MonoBehaviour
{
    public float captureInterval = 5f; // frequency
    public string pythonExePath = "python"; 
    public string scriptPath = ".py"; 
    public string screenshotsFolder = "CapturedImages";
    public GameObject warningPanel; 
    public Text warningText; 

    private float timer = 0f;
    private string lastScreenshotPath = "";

    void Start()
    {
        if (warningPanel != null)
            warningPanel.SetActive(false);
        Directory.CreateDirectory(Path.Combine(Application.persistentDataPath, screenshotsFolder));
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= captureInterval)
        {
            timer = 0f;
            StartCoroutine(CaptureAndCheck());
        }
    }

    IEnumerator CaptureAndCheck()
    {
        string screenshotPath = Path.Combine(Application.persistentDataPath, screenshotsFolder, "frame" + Time.frameCount + ".png");
        ScreenCapture.CaptureScreenshot(screenshotPath);
        lastScreenshotPath = screenshotPath;
        yield return new WaitForSeconds(0.5f); // waiting
        yield return StartCoroutine(RunPythonCheck(screenshotPath));
    }

    IEnumerator RunPythonCheck(string imagePath)
    {
        string absScriptPath = Path.GetFullPath(scriptPath);
        ProcessStartInfo start = new ProcessStartInfo();
        start.FileName = pythonExePath;
        start.Arguments = $"\"{absScriptPath}\" \"{imagePath}\"";
        start.UseShellExecute = false;
        start.RedirectStandardOutput = true;
        start.RedirectStandardError = true;
        start.CreateNoWindow = true;

        string result = "";
        string error = "";
        using (Process process = Process.Start(start))
        {
            result = process.StandardOutput.ReadToEnd();
            error = process.StandardError.ReadToEnd();
            process.WaitForExit();
        }
        if (!string.IsNullOrEmpty(error))
        {
            UnityEngine.Debug.LogError("Python Error: " + error);
            yield break;
        }
        bool isPrivacy = false;
        try
        {
            var json = JsonUtility.FromJson<PrivacyResult>(result);
            isPrivacy = json.privacy;
        }
        catch
        {
            UnityEngine.Debug.LogError("error: " + result);
        }
        if (isPrivacy)
        {
            ShowWarningUI();
        }
        else
        {
            HideWarningUI();
        }
        yield return null;
    }

    void ShowWarningUI()
    {
        if (warningPanel != null && warningText != null)
        {
            warningText.text = "⚠️ Security Alert！";
            warningPanel.SetActive(true);
        }
    }

    void HideWarningUI()
    {
        if (warningPanel != null)
            warningPanel.SetActive(false);
    }

    [System.Serializable]
    public class PrivacyResult
    {
        public bool privacy;
    }

} 
