from typing import List


def roman_sort(nums: List[str]) -> List[str]:
    """
    Contributed by ChatGPT.
    """
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    sorted_nums = sorted(nums, key=lambda x: sum(values[c.upper()] for c in x))
    return sorted_nums


def roman_sort_with_ints(arr):
    """
    Contributed by ChatGPT, who didn't know how to use .upper()
    """
    roman_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}

    def roman_to_int(num):
        if isinstance(num, str):
            num = num.upper()
        result = 0
        for i in range(len(num)):
            if i > 0 and roman_dict[num[i]] > roman_dict[num[i - 1]]:
                result += roman_dict[num[i]] - 2 * roman_dict[num[i - 1]]
            else:
                result += roman_dict[num[i]]
        return result

    def int_or_roman(elem):
        try:
            return int(elem)
        except ValueError:
            return roman_to_int(elem)

    sorted_arr = sorted(arr, key=int_or_roman)
    return sorted_arr
