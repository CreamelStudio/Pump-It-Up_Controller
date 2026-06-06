using DG.Tweening;
using System;
using System.Collections;
using System.IO.Ports;
using UnityEngine;
using UnityEngine.UI;

public class PumpController : MonoBehaviour
{
    public static PumpController Instance;

    public Image connectingBar;

    public SerialPort serial;
    public int baudRate = 115200;

    private bool isConnected = false;
    private bool isConnecting = false;

    private void Awake()
    {
        if (Instance == null) Instance = this;
        else
        {
            Destroy(gameObject);
            return;
        }
    }

    private void Start()
    {
        StartCoroutine(Co_ConnectArduino());
        StartCoroutine(Co_ConnectingBarBlank());
    }

    IEnumerator Co_ConnectArduino()
    {
        if (isConnecting) yield break;
        isConnecting = true;

        while (!isConnected)
        {
            string[] ports = SerialPort.GetPortNames();

            foreach (string portName in ports)
            {
                SerialPort testPort = null;

                Debug.Log($"포트 확인 중: {portName}");

                bool openSuccess = false;

                try
                {
                    testPort = new SerialPort(portName, baudRate);
                    testPort.ReadTimeout = 50;
                    testPort.WriteTimeout = 300;
                    testPort.NewLine = "\n";

                    // 아두이노가 포트 열릴 때 리셋되는 경우 안정화용
                    testPort.DtrEnable = true;
                    testPort.RtsEnable = true;

                    testPort.Open();

                    openSuccess = true;
                }
                catch (Exception e)
                {
                    Debug.Log($"포트 열기 실패: {portName} / {e.Message}");
                    SafeClose(testPort);
                }

                if (!openSuccess)
                {
                    yield return null;
                    continue;
                }

                // 아두이노 리셋 대기
                yield return new WaitForSeconds(1.5f);

                SafeDiscardInBuffer(testPort);

                bool writeSuccess = SafeWriteLine(testPort, "PING");

                if (!writeSuccess)
                {
                    SafeClose(testPort);
                    yield return null;
                    continue;
                }

                float startTime = Time.realtimeSinceStartup;
                bool found = false;
                string buffer = "";

                while (Time.realtimeSinceStartup - startTime < 2f)
                {
                    string chunk = SafeReadExisting(testPort);

                    if (!string.IsNullOrEmpty(chunk))
                    {
                        buffer += chunk;

                        Debug.Log($"[{portName}] {chunk.Trim()}");

                        if (buffer.Contains("PONG"))
                        {
                            found = true;
                            break;
                        }
                    }

                    // 중요: try/catch 밖이라 가능함
                    yield return null;
                }

                if (found)
                {
                    serial = testPort;
                    isConnected = true;
                    isConnecting = false;

                    Debug.Log($"아두이노 연결 성공: {portName}");

                    yield break;
                }

                SafeClose(testPort);

                yield return null;
            }

            Debug.LogWarning("아두이노를 찾지 못함. 다시 검색 중...");
            yield return new WaitForSeconds(0.5f);
        }

        isConnecting = false;
    }

    private string SafeReadExisting(SerialPort port)
    {
        try
        {
            if (port == null) return "";
            if (!port.IsOpen) return "";
            if (port.BytesToRead <= 0) return "";

            return port.ReadExisting();
        }
        catch (Exception e)
        {
            Debug.Log($"시리얼 읽기 실패: {e.Message}");
            return "";
        }
    }

    private bool SafeWriteLine(SerialPort port, string message)
    {
        try
        {
            if (port == null) return false;
            if (!port.IsOpen) return false;

            port.WriteLine(message);
            return true;
        }
        catch (Exception e)
        {
            Debug.Log($"시리얼 쓰기 실패: {e.Message}");
            return false;
        }
    }

    private void SafeDiscardInBuffer(SerialPort port)
    {
        try
        {
            if (port != null && port.IsOpen)
                port.DiscardInBuffer();
        }
        catch (Exception e)
        {
            Debug.Log($"버퍼 비우기 실패: {e.Message}");
        }
    }

    private void SafeClose(SerialPort port)
    {
        try
        {
            if (port != null && port.IsOpen)
                port.Close();
        }
        catch (Exception e)
        {
            Debug.Log($"포트 닫기 실패: {e.Message}");
        }
    }

    IEnumerator Co_ConnectingBarBlank()
    {
        while (!isConnected)
        {
            if (connectingBar != null)
            {
                connectingBar.DOKill();
                connectingBar.DOColor(new Color(1, 0, 0, 1), 0.5f);
            }

            yield return new WaitForSeconds(0.5f);

            if (connectingBar != null)
            {
                connectingBar.DOKill();
                connectingBar.DOColor(new Color(1, 0, 0, 0), 0.5f);
            }

            yield return new WaitForSeconds(0.5f);
        }

        if (connectingBar != null)
        {
            connectingBar.DOKill();
            connectingBar.DOColor(new Color(0, 1, 0, 1), 0.5f);
        }
    }

    private void OnApplicationQuit()
    {
        SafeClose(serial);
    }
}