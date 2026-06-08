using UnityEngine;
using DG.Tweening;
public class BattleSystem : MonoBehaviour
{
    public int player1Click = 0;
    public int player2Click = 0;

    public float timer = 0f;
    public float gameDuration = 10f;

    public GameObject middleObject;
    public GameObject movingObject;
    public float middleMovePerClick = 0.5f;

    bool isPlaying;
    Transform targetTransform;
    Vector3 centerPosition;

    void Start()
    {
        GameStart();
    }

    void Update()
    {
        if (!isPlaying) return;

        timer += Time.deltaTime;
        ReadControllerInput();
        UpdateMiddleObject();

        if (timer >= gameDuration)
        {
            StopGame();
            Debug.Log("Game Over!");
            Debug.Log("Player 1 Clicks: " + player1Click);
            Debug.Log("Player 2 Clicks: " + player2Click);
        }
    }

    void GameStart()
    {
        isPlaying = true;
        timer = 0f;
        player1Click = 0;
        player2Click = 0;
        CacheMiddlePosition();
        UpdateMiddleObject();
    }

    void StopGame()
    {
        if (!isPlaying) return;

        isPlaying = false;
    }

    void ReadControllerInput()
    {
        NewInput.UpdateFromKeyboard();

        if (NewInput.GetButtonDown(PumpButton.UpLeft) || NewInput.GetButtonDown(PumpButton.UpRight))
        {
            player1Click++;
            Debug.Log("Player 1 Clicks: " + player1Click);
        }

        if (NewInput.GetButtonDown(PumpButton.DownLeft) || NewInput.GetButtonDown(PumpButton.DownRight))
        {
            player2Click++;
            Debug.Log("Player 2 Clicks: " + player2Click);
        }
    }

    private void UpdateMiddleObject()
    {
        if (middleObject == null) return;

        Vector3 targetPosition = centerPosition;
        targetPosition.x += (player1Click - player2Click) * middleMovePerClick;
        targetTransform.DOMoveX(targetPosition.x, 0.1f).SetEase(Ease.OutQuad);

        if(Mathf.Abs(player1Click - player2Click) >= 100) {
            StopGame();
            Debug.Log("Game Over!");
            Debug.Log("Player 1 Clicks: " + player1Click);
            Debug.Log("Player 2 Clicks: " + player2Click);
        }
    }

    void CacheMiddlePosition()
    {
        if (middleObject == null) return;

        targetTransform = movingObject != null ? movingObject.transform : middleObject.transform;
        centerPosition = middleObject.transform.position;
    }

    void OnDestroy()
    {
    }
}
