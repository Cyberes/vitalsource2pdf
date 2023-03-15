from typing import List

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


def try_convert_int(item):
    try:
        return int(item)
    except ValueError:
        return item


def move_integers_to_end(lst):
    non_integers = []
    integers = []
    for elem in lst:
        if isinstance(elem, int):
            integers.append(elem)
        else:
            non_integers.append(elem)
    return non_integers + integers


def move_romans_to_front(arr):
    arr_sorted = sorted(arr, key=lambda x: isinstance(x, int))
    arr_sorted.insert(0, arr_sorted.pop(arr_sorted.index(0)))
    return arr_sorted
