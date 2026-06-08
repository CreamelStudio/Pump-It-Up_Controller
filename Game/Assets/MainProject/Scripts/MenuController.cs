using UnityEngine;
using UnityEngine.SceneManagement;

public enum MenuOption
{
    CoursePlay,
    Battle,
    Gun,
    Timing,
    Bomb,
    Random
}

public class MenuController : MonoBehaviour
{
    public MenuOption NowSelectMenu = MenuOption.CoursePlay;

    private void Start()
    {
        NewInput.PumpButtonChanged += ControllerInput;
    }

    private void ControllerInput(PumpInputEvent inputEvent)
    {
        if (inputEvent.IsPressed)
        {
            switch (inputEvent.Binding.Button)
            {
                case PumpButton.UpLeft:
                    NowSelectMenu = (MenuOption)(((int)NowSelectMenu + 1) % System.Enum.GetValues(typeof(MenuOption)).Length);
                    break;
                case PumpButton.UpRight:
                    NowSelectMenu = (MenuOption)(((int)NowSelectMenu - 1 + System.Enum.GetValues(typeof(MenuOption)).Length) % System.Enum.GetValues(typeof(MenuOption)).Length);
                    break;
                case PumpButton.DownLeft:
                    NowSelectMenu = (MenuOption)(((int)NowSelectMenu + 1) % System.Enum.GetValues(typeof(MenuOption)).Length);
                    break;
                case PumpButton.DownRight:
                    NowSelectMenu = (MenuOption)(((int)NowSelectMenu - 1 + System.Enum.GetValues(typeof(MenuOption)).Length) % System.Enum.GetValues(typeof(MenuOption)).Length);
                    break;
                case PumpButton.Center:
                    SceneManager.LoadScene(NowSelectMenu.ToString());
                    break;
            }
        }
    }
}
