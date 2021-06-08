from itertools import islice


class TransformationUtils:
    # Chunks list into multiple list of size provided as parameter
    #
    # Parameters:
    #
    # it : Iterator
    # size : Size of output list
    # padval : padding if needed

    _no_padding = object()

    @staticmethod
    def chunk(it, size, padval=_no_padding):
        it = iter(it)
        chunker = iter(lambda: tuple(islice(it, size)), ())
        yield from chunker

    # Iterate over List to fetch value
    #
    # Parameters:
    #
    # input_seg : Input Segment (Dict)
    # itr : Iterator
    # list_ : List containing field path

    @staticmethod
    def get_data(input_seg, itr, list_):
        seg = input_seg
        path = ""
        while itr < len(list_):
            path = path + list_[itr] + '.'
            if type(seg) != type([1, 2]):
                if hasattr(seg, list_[itr]):
                    seg = eval('seg.' + list_[itr])
                    itr += 1
                else:
                    return None
            else:
                seg = seg[0]
        return seg

    @staticmethod
    def add_key(item_map, key, val):
        if val:
            item_map[key] = val

    # Responsible to find out common node between source field and condition field
    # Such that iterating over again is avoided
    #
    # Parameters:
    #
    # path_list : Source field path
    # cond_list : Condition field path

    @staticmethod
    def find_common_node(path_list, cond_list):
        stack = []
        if len(path_list) <= len(cond_list):
            itr = 0
            while itr < len(path_list):
                if cond_list[itr] == path_list[itr]:
                    stack.append(path_list[itr])
                itr += 1
        elif len(path_list) > len(cond_list):
            itr = 0
            while itr < len(cond_list):
                if cond_list[itr] is not None:
                    if cond_list[itr] == path_list[itr]:
                        stack.append(path_list[itr])
                itr += 1
        else:
            print("else")
        return stack.pop()
