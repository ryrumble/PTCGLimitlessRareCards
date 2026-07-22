from regulation_filter import (
    filter_g_regulation_cards,
    is_duplicate_skip,
    is_g_regulation,
)


class TestIsGRegulation:
    def test_full_g_set(self):
        assert is_g_regulation("SVI", 1) is True
        assert is_g_regulation("PAL", 100) is True
        assert is_g_regulation("MEW", 50) is True

    def test_full_i_set(self):
        assert is_g_regulation("WHT", 1) is False
        assert is_g_regulation("MEG", 50) is False
        assert is_g_regulation("PFL", 100) is False

    def test_mixed_set_jtg(self):
        assert is_g_regulation("JTG", 155) is True
        assert is_g_regulation("JTG", 1) is False

    def test_mixed_set_twm(self):
        assert is_g_regulation("TWM", 1) is True
        assert is_g_regulation("TWM", 161) is False

    def test_mixed_set_scr(self):
        assert is_g_regulation("SCR", 1) is True
        assert is_g_regulation("SCR", 2) is False

    def test_unknown_set(self):
        assert is_g_regulation("FAKE", 1) is False

    def test_case_insensitive(self):
        assert is_g_regulation("svi", 1) is True
        assert is_g_regulation("jtg", 155) is True


class TestIsDuplicateSkip:
    def test_known_duplicate(self):
        assert is_duplicate_skip("ASC", 16) is True

    def test_non_duplicate(self):
        assert is_duplicate_skip("ASC", 1) is False

    def test_unknown_set(self):
        assert is_duplicate_skip("JTG", 1) is False

    def test_case_insensitive(self):
        assert is_duplicate_skip("asc", 16) is True


class TestFilterGRegulationCards:
    def test_skip_g_cards_with_cardresult_objects(self):
        class FakeCard:
            def __init__(self, set_code, card_number):
                self.set_code = set_code
                self.card_number = card_number

        cards = [FakeCard("SVI", 1), FakeCard("JTG", 155), FakeCard("JTG", 1)]
        filtered = filter_g_regulation_cards(cards, exclude_g=True)
        assert len(filtered) == 1
        assert filtered[0].card_number == 1

    def test_include_all_when_exclude_g_false(self):
        class FakeCard:
            def __init__(self, set_code, card_number):
                self.set_code = set_code
                self.card_number = card_number

        cards = [FakeCard("SVI", 1), FakeCard("JTG", 1)]
        filtered = filter_g_regulation_cards(cards, exclude_g=False)
        assert len(filtered) == 2

    def test_filter_tuples(self):
        cards = [("SVI", 1), ("JTG", 155), ("JTG", 1)]
        filtered = filter_g_regulation_cards(cards, exclude_g=True)
        assert len(filtered) == 1
        assert filtered[0] == ("JTG", 1)

    def test_empty_list(self):
        assert filter_g_regulation_cards([], exclude_g=True) == []

    def test_no_g_regulation_match_attr(self):
        class NoAttr:
            pass

        cards = [NoAttr()]
        filtered = filter_g_regulation_cards(cards, exclude_g=True)
        assert len(filtered) == 0
