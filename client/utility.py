import os


def pos_to_str(pos):
    s = ''
    for i in range(len(pos)):
        x, y = pos[i]
        s += chr(ord('a') + x) + str(y + 1)
    return s


def str_to_pos(s):
    pos = []
    i = 0
    s = s.lower()
    while i < len(s):
        x = ord(s[i]) - ord('a')
        y = ord(s[i + 1]) - ord('0')
        if i + 2 < len(s) and s[i + 2].isdigit():
            y = y * 10 + ord(s[i + 2]) - ord('0') - 1
            i += 3
        else:
            y = y - 1
            i += 2
        pos += [(x, y)]
    return pos


def psq_to_psq(_psq, board_size):
    psq = ''
    # psq += 'Piskvorky ' + str(board_size) + "x" + str(board_size) + "," + " 11:11," + " 0\n"
    tt = [0, 0]
    for i in range(len(_psq)):
        x, y, t = _psq[i]
        psq += str(x + 1) + "," + str(y + 1) + "," + str(t - tt[i % 2]) + "\n"
        tt[i % 2] = t
    return psq


def get_dir_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


if __name__ == '__main__':
    print(psq_to_psq([(18, 12, 36), (11, 11, 146), (18, 10, 72), (10, 10, 291)], 20))
