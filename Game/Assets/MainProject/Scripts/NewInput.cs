using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public enum PumpButton
{
    UpLeft,
    UpRight,
    Center,
    DownLeft,
    DownRight,
    Unknown
}

public readonly struct PumpButtonBinding
{
    public PumpButtonBinding(int pin, PumpButton button, string keyName, Key key)
    {
        Pin = pin;
        Button = button;
        KeyName = keyName;
        Key = key;
    }

    public int Pin { get; }
    public PumpButton Button { get; }
    public string KeyName { get; }
    public Key Key { get; }
}

public readonly struct PumpInputEvent
{
    public PumpInputEvent(PumpButtonBinding binding, bool isPressed)
    {
        Binding = binding;
        IsPressed = isPressed;
    }

    public PumpButtonBinding Binding { get; }
    public bool IsPressed { get; }
    public bool IsReleased => !IsPressed;
}

public static class NewInput
{
    public static event Action<PumpInputEvent> PumpButtonChanged;
    public static event Action<IReadOnlyDictionary<int, PumpButtonBinding>> PumpKeyMapChanged;

    static readonly Dictionary<int, PumpButtonBinding> bindingsByPin = new();
    static readonly Dictionary<PumpButton, PumpButtonBinding> bindingsByButton = new();
    static readonly Dictionary<PumpButton, int> pressedFrameByButton = new();
    static readonly Dictionary<PumpButton, int> releasedFrameByButton = new();
    static readonly HashSet<PumpButton> pressedButtons = new();
    static bool defaultBindingsLoaded;

    public static IReadOnlyDictionary<int, PumpButtonBinding> BindingsByPin => bindingsByPin;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Initialize()
    {
        LoadDefaultBindings();

        GameObject updaterObject = new GameObject("NewInput");
        UnityEngine.Object.DontDestroyOnLoad(updaterObject);
        updaterObject.AddComponent<NewInputUpdater>();
    }

    public static bool GetButton(PumpButton button)
    {
        LoadDefaultBindings();
        return pressedButtons.Contains(button);
    }

    public static bool GetButtonDown(PumpButton button)
    {
        LoadDefaultBindings();
        return pressedFrameByButton.TryGetValue(button, out int frame) && frame == Time.frameCount;
    }

    public static bool GetButtonUp(PumpButton button)
    {
        LoadDefaultBindings();
        return releasedFrameByButton.TryGetValue(button, out int frame) && frame == Time.frameCount;
    }

    public static bool TryGetBinding(PumpButton button, out PumpButtonBinding binding)
    {
        LoadDefaultBindings();
        return bindingsByButton.TryGetValue(button, out binding);
    }

    public static bool TryGetBinding(int pin, out PumpButtonBinding binding)
    {
        LoadDefaultBindings();
        return bindingsByPin.TryGetValue(pin, out binding);
    }

    public static void SetBinding(int pin, string keyName)
    {
        PumpButton button = PumpButtonMap.FromPin(pin);
        PumpButtonBinding binding = new PumpButtonBinding(pin, button, keyName, ToInputSystemKey(keyName));

        bindingsByPin[pin] = binding;

        if (button != PumpButton.Unknown)
        {
            bindingsByButton[button] = binding;
        }

        PumpKeyMapChanged?.Invoke(BindingsByPin);
    }

    public static void SetPressed(int pin, bool isPressed)
    {
        if (!bindingsByPin.TryGetValue(pin, out PumpButtonBinding binding))
        {
            binding = new PumpButtonBinding(pin, PumpButtonMap.FromPin(pin), string.Empty, Key.None);
            bindingsByPin[pin] = binding;
        }

        SetPressed(binding, isPressed);
    }

    public static void UpdateFromKeyboard()
    {
        LoadDefaultBindings();

        Keyboard keyboard = Keyboard.current;
        if (keyboard == null) return;

        foreach (PumpButtonBinding binding in bindingsByButton.Values)
        {
            if (binding.Key == Key.None) continue;

            var keyControl = keyboard[binding.Key];
            if (keyControl == null) continue;

            bool isPressed = keyControl.isPressed;
            SetPressed(binding, isPressed);
        }
    }

    static void SetPressed(PumpButtonBinding binding, bool isPressed)
    {
        bool changed = false;

        if (binding.Button != PumpButton.Unknown)
        {
            if (isPressed)
            {
                if (pressedButtons.Add(binding.Button))
                {
                    pressedFrameByButton[binding.Button] = Time.frameCount;
                    changed = true;
                }
            }
            else
            {
                if (pressedButtons.Remove(binding.Button))
                {
                    releasedFrameByButton[binding.Button] = Time.frameCount;
                    changed = true;
                }
            }
        }

        if (changed)
        {
            PumpButtonChanged?.Invoke(new PumpInputEvent(binding, isPressed));
        }
    }

    public static void ReleaseAll()
    {
        pressedButtons.Clear();
        pressedFrameByButton.Clear();
        releasedFrameByButton.Clear();
    }

    static void LoadDefaultBindings()
    {
        if (defaultBindingsLoaded) return;

        defaultBindingsLoaded = true;
        SetBinding(10, "q");
        SetBinding(11, "e");
        SetBinding(9, "space");
        SetBinding(7, "z");
        SetBinding(8, "c");
    }

    static Key ToInputSystemKey(string keyName)
    {
        if (string.IsNullOrWhiteSpace(keyName)) return Key.None;

        switch (keyName.Trim().ToLowerInvariant())
        {
            case "space": return Key.Space;
            case "enter":
            case "return": return Key.Enter;
            case "esc":
            case "escape": return Key.Escape;
            case "tab": return Key.Tab;
            case "backspace": return Key.Backspace;
            case "delete": return Key.Delete;
            case "up": return Key.UpArrow;
            case "down": return Key.DownArrow;
            case "left": return Key.LeftArrow;
            case "right": return Key.RightArrow;
            case "shift": return Key.LeftShift;
            case "ctrl":
            case "control": return Key.LeftCtrl;
            case "alt": return Key.LeftAlt;
            case "home": return Key.Home;
            case "end": return Key.End;
            case "pageup": return Key.PageUp;
            case "pagedown": return Key.PageDown;
            case "f1": return Key.F1;
            case "f2": return Key.F2;
            case "f3": return Key.F3;
            case "f4": return Key.F4;
            case "f5": return Key.F5;
            case "f6": return Key.F6;
            case "f7": return Key.F7;
            case "f8": return Key.F8;
            case "f9": return Key.F9;
            case "f10": return Key.F10;
            case "f11": return Key.F11;
            case "f12": return Key.F12;
        }

        if (keyName.Length == 1)
        {
            char c = char.ToLowerInvariant(keyName[0]);
            if (c >= 'a' && c <= 'z') return (Key)((int)Key.A + (c - 'a'));
            if (c >= '0' && c <= '9') return (Key)((int)Key.Digit0 + (c - '0'));
        }

        return Key.None;
    }
}

public class NewInputUpdater : MonoBehaviour
{
    void Update()
    {
        NewInput.UpdateFromKeyboard();
    }
}

public static class PumpButtonMap
{
    public static PumpButton FromPin(int pin)
    {
        switch (pin)
        {
            case 10: return PumpButton.UpLeft;
            case 11: return PumpButton.UpRight;
            case 9: return PumpButton.Center;
            case 7: return PumpButton.DownLeft;
            case 8: return PumpButton.DownRight;
            default: return PumpButton.Unknown;
        }
    }
}
