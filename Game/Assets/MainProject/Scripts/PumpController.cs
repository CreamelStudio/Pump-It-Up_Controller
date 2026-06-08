using System;
using System.Collections;
using System.IO;
using System.IO.Ports;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;

public class PumpController : MonoBehaviour
{
    public static PumpController Instance;

    public Image connectingBar;
    public int baudRate = 115200;

    public SerialPort serial;

    bool isConnected;
    string serialBuffer = "";

    void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else Destroy(gameObject);
    }

    void Start()
    {
        StartCoroutine(ConnectArduino());
        StartCoroutine(BlinkBar());
    }

    void Update()
    {
        if (!isConnected || serial == null || !serial.IsOpen) return;

        ReadArduinoMessages(serial);
    }

    IEnumerator ConnectArduino()
    {
        while (!isConnected)
        {
            foreach (string port in GetPorts())
            {
                Debug.Log("Checking port: " + port);

                SerialPort sp = null;

                try
                {
                    sp = new SerialPort(port, baudRate)
                    {
                        ReadTimeout = 50,
                        WriteTimeout = 300,
                        NewLine = "\n",
                        DtrEnable = true
                    };

                    sp.Open();
                }
                catch
                {
                    ClosePort(sp);
                    continue;
                }

                yield return new WaitForSeconds(1.5f);

                try
                {
                    sp.DiscardInBuffer();
                    sp.WriteLine("PING");
                }
                catch
                {
                    ClosePort(sp);
                    continue;
                }

                float timer = 0f;
                string buffer = "";

                while (timer < 2f)
                {
                    try
                    {
                        if (sp.BytesToRead > 0)
                            buffer += sp.ReadExisting();
                    }
                    catch
                    {
                        break;
                    }

                    if (buffer.Contains("PONG"))
                    {
                        serial = sp;
                        isConnected = true;
                        serialBuffer = "";

                        Debug.Log("Arduino connected: " + port);
                        RequestKeyMap();
                        yield break;
                    }

                    timer += Time.unscaledDeltaTime;
                    yield return null;
                }

                ClosePort(sp);
            }

            Debug.LogWarning("Arduino not found. Retrying...");
            yield return new WaitForSeconds(0.5f);
        }
    }

    string[] GetPorts()
    {
        #if UNITY_EDITOR_OSX || UNITY_STANDALONE_OSX
        if (Directory.Exists("/dev"))
            return Directory.GetFiles("/dev", "cu.usb*");

        return Array.Empty<string>();
        #else
        return SerialPort.GetPortNames();
        #endif
    }

    IEnumerator BlinkBar()
    {
        while (!isConnected)
        {
            if (connectingBar != null)
                connectingBar.DOColor(new Color(1, 0, 0, 1), 0.5f);

            yield return new WaitForSeconds(0.5f);

            if (connectingBar != null)
                connectingBar.DOColor(new Color(1, 0, 0, 0), 0.5f);

            yield return new WaitForSeconds(0.5f);
        }

        if (connectingBar != null)
            connectingBar.DOColor(new Color(0, 1, 0, 1), 0.5f);
    }

    void RequestKeyMap()
    {
        try
        {
            serial?.WriteLine("PRINT");
        }
        catch (Exception ex)
        {
            Debug.LogWarning("Failed to request Arduino keymap: " + ex.Message);
        }
    }

    void ReadArduinoMessages(SerialPort sp)
    {
        try
        {
            if (sp.BytesToRead <= 0) return;

            serialBuffer += sp.ReadExisting();
        }
        catch (Exception ex)
        {
            Debug.LogWarning("Failed to read Arduino serial data: " + ex.Message);
            return;
        }

        while (TryReadLine(out string line))
        {
            HandleArduinoLine(line);
        }
    }

    bool TryReadLine(out string line)
    {
        int newlineIndex = serialBuffer.IndexOf('\n');

        if (newlineIndex < 0)
        {
            line = null;
            return false;
        }

        line = serialBuffer.Substring(0, newlineIndex).Trim();
        serialBuffer = serialBuffer.Substring(newlineIndex + 1);
        return true;
    }

    void HandleArduinoLine(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return;

        string[] parts = line.Split(',').Select(part => part.Trim()).ToArray();
        if (parts.Length == 0) return;

        switch (parts[0])
        {
            case "MAP":
                HandleKeyMapLine(parts);
                break;
        }
    }

    void HandleKeyMapLine(string[] parts)
    {
        if (parts.Length < 3) return;
        if (!int.TryParse(parts[1], out int pin)) return;

        NewInput.SetBinding(pin, parts[2]);
    }

    void ClosePort(SerialPort sp)
    {
        try
        {
            if (sp != null && sp.IsOpen)
                sp.Close();
        }
        catch { }
    }

    void OnApplicationQuit()
    {
        NewInput.ReleaseAll();
        ClosePort(serial);
    }
}
