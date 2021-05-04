class OrderedDict:
    def pop(self, key=None):
        if not key:
            key = self.ord_dict[-1]

        val = self.prop_dict[key]

        self.__delitem__(key)

        return val

    def get(self, key):
        return self.prop_dict.get(key)

    def update(self, update_dict):
        if not isinstance(update_dict, dict):
            for key, val in update_dict:
                self.__setitem__(key, val)

            return

        for key, val in update_dict.items():
            self.__setitem__(key, val)

    def keys(self):
        return KeyView(self)

    def items(self):
        return ItemView(self)

    def values(self):
        return ValueView(self)

    def __delitem__(self, key):
        del self.prop_dict[key]

        self.ord_dict = [item for item in self.ord_dict if (item != key)]

    def __eq__(self, other):
        if self.ord_dict != other.ord_dict:
            return False

        if self.prop_dict != other.prop_dict:
            return False

        return True

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.prop_dict[self.ord_dict[key]]

        return self.prop_dict[key]

    def __init__(self, new_dict=None):
        self.prop_dict = new_dict if new_dict else {}
        self.ord_dict = [key for key in self.prop_dict]

    def __iter__(self):
        yield from self.ord_dict

    def __repr__(self):
        repr_string = "OrdDict{"
        repr_string += ", ".join([(str(k) + ": " + str(v)) for k, v in self.prop_dict.items()])
        repr_string += "}"

        return repr_string

    def __reversed__(self):
        yield from reversed(self.prop_dict)

    def __setitem__(self, key, value):
        if key in self.prop_dict:
            self.prop_dict[key] = value
        else:
            self.prop_dict[key] = value
            self.ord_dict.append(key)

    def _find(self, key):
        for k in self.ord_dict:
            if self.prop_dict.get(k) == key:
                return k
        return None


class KeyView:
    def __init__(self, ord_dict):
        self.ord_dict = ord_dict

    def __iter__(self):
        return iter(self.ord_dict.ord_dict)

    def __reversed__(self):
        return reversed(self.ord_dict.ord_dict)


class ValueView:
    def __init__(self, ord_dict):
        self.ord_dict = ord_dict

    def __iter__(self):
        return (self.ord_dict.prop_dict.get(key) for key in self.ord_dict.ord_dict)

    def __reversed__(self):
        return (self.ord_dict.prop_dict.get(key) for key in reversed(self.ord_dict.ord_dict))


class ItemView:
    def __init__(self, ord_dict):
        self.ord_dict = ord_dict

    def __iter__(self):
        return ((key, self.ord_dict.prop_dict.get(key)) for key in self.ord_dict.ord_dict)

    def __reversed__(self):
        return ((key, self.ord_dict.prop_dict.get(key)) for key in reversed(self.ord_dict.ord_dict))
