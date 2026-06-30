from app.config.profiles import PROFILES, get_profile, primary_profiles


def test_primary_profiles_define_three_complexity_levels() -> None:
    profiles = primary_profiles()

    assert [profile.name for profile in profiles] == [
        "fast",
        "balanced",
        "reasoning",
    ]
    assert [profile.chat_model for profile in profiles] == [
        "llama3.2:3b",
        "qwen3:8b",
        "deepseek-r1:8b",
    ]


def test_only_three_profiles_are_supported() -> None:
    assert list(PROFILES) == [
        "fast",
        "balanced",
        "reasoning",
    ]
    assert get_profile("balanced").name == "balanced"
