using System;
using System.Collections;
using System.IO;
using System.IO.Ports;
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

    void Awake()
    {
        // 싱글톤 설정
        if (Instance == null) Instance = this;
        else Destroy(gameObject);
    }

    void Start()
    {
        // 아두이노 자동 연결 시작
        StartCoroutine(ConnectArduino());

        // 연결 상태 UI 깜빡임 시작
        StartCoroutine(BlinkBar());
    }

    IEnumerator ConnectArduino()
    {
        // 연결될 때까지 계속 반복
        while (!isConnected)
        {
            // 윈도우 / 맥에 맞는 포트 목록 가져오기
            foreach (string port in GetPorts())
            {
                Debug.Log("포트 확인: " + port);

                SerialPort sp = null;

                // 포트 열기 시도
                try
                {
                    sp = new SerialPort(port, baudRate);

                    // ReadLine 같은 블로킹 방지용 짧은 타임아웃
                    sp.ReadTimeout = 50;
                    sp.WriteTimeout = 300;

                    // 아두이노 Serial.println 기준 줄바꿈
                    sp.NewLine = "\n";

                    // 일부 아두이노 보드에서 연결 안정화용
                    sp.DtrEnable = true;

                    sp.Open();
                }
                catch
                {
                    // 포트 열기 실패하면 다음 포트 검사
                    ClosePort(sp);
                    continue;
                }

                // 아두이노는 포트가 열리면 리셋되는 경우가 있어서 잠깐 대기
                yield return new WaitForSeconds(1.5f);

                // 기존에 남아있던 데이터 비우고 PING 전송
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

                // 2초 동안 PONG 응답 대기
                while (timer < 2f)
                {
                    try
                    {
                        // 데이터가 있을 때만 읽음
                        // ReadExisting은 ReadLine보다 덜 멈춤
                        if (sp.BytesToRead > 0)
                            buffer += sp.ReadExisting();
                    }
                    catch
                    {
                        // 읽기 실패하면 이 포트는 포기
                        break;
                    }

                    // 아두이노가 PONG을 보내면 연결 성공
                    if (buffer.Contains("PONG"))
                    {
                        serial = sp;
                        isConnected = true;

                        Debug.Log("아두이노 연결 성공: " + port);
                        yield break;
                    }

                    timer += Time.unscaledDeltaTime;

                    // try/catch 밖이라 yield 가능
                    yield return null;
                }

                // PONG 못 받았으면 포트 닫고 다음 포트 확인
                ClosePort(sp);
            }

            Debug.LogWarning("아두이노 못 찾음. 재시도...");

            // 너무 빠르게 반복하지 않게 잠깐 대기
            yield return new WaitForSeconds(0.5f);
        }
    }

    string[] GetPorts()
    {
        #if UNITY_EDITOR_OSX || UNITY_STANDALONE_OSX
                // macOS에서는 아두이노가 보통 /dev/cu.usb... 형태로 잡힘
                if (Directory.Exists("/dev"))
                    return Directory.GetFiles("/dev", "cu.usb*");

                return Array.Empty<string>();
        #else
                // Windows에서는 COM3, COM4 같은 포트가 여기서 잡힘
                return SerialPort.GetPortNames();
        #endif
    }

    IEnumerator BlinkBar()
    {
        // 연결 전에는 빨간색으로 깜빡임
        while (!isConnected)
        {
            if (connectingBar != null)
                connectingBar.DOColor(new Color(1, 0, 0, 1), 0.5f);

            yield return new WaitForSeconds(0.5f);

            if (connectingBar != null)
                connectingBar.DOColor(new Color(1, 0, 0, 0), 0.5f);

            yield return new WaitForSeconds(0.5f);
        }

        // 연결되면 초록색 고정
        if (connectingBar != null)
            connectingBar.DOColor(new Color(0, 1, 0, 1), 0.5f);
    }

    void ClosePort(SerialPort sp)
    {
        // 포트 안전하게 닫기
        try
        {
            if (sp != null && sp.IsOpen)
                sp.Close();
        }
        catch { }
    }

    void OnApplicationQuit()
    {
        // 게임 종료 시 포트 닫기
        ClosePort(serial);
    }
}