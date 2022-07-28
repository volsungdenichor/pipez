from pipez.seq import seq

if __name__ == '__main__':
    (range(1, 100)
     >> seq.flat_map(
                lambda z: range(1, z + 1) >> seq.flat_map(
                    lambda x: range(x, z + 1) >> seq.filter_map(
                        lambda y: (x, y, z) if x * x + y * y == z * z else None)))
     >> seq.for_each(print))
