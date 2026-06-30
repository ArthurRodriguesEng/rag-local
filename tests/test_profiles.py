from app.config.profiles import PROFILES, get_profile, primary_profiles


def test_primary_profiles_define_five_complexity_levels() -> None:
    profiles = primary_profiles()

    assert [profile.name for profile in profiles] == [
        "fast",
        "balanced",
        "reasoning",
        "robust",
        "max",
    ]
    assert [profile.chat_model for profile in profiles] == [
        "qwen3:8b",
        "gemma3:12b",
        "deepseek-r1:8b",
        "qwen3:14b",
        "mistral-small3.2:24b",
    ]


def test_only_five_profiles_are_supported() -> None:
    assert list(PROFILES) == [
        "fast",
        "balanced",
        "reasoning",
        "robust",
        "max",
    ]
    assert get_profile("balanced").name == "balanced"
