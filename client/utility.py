def pos_to_str(pos):
    s = ''
    for i in xrange(len(pos)):
        x, y = pos[i]
        s += chr(ord('a')+x) + str(y+1)
    return s

def str_to_pos(s):
    pos = []
    i = 0
    s = s.lower()
    while i < len(s):
        x = ord(s[i]) - ord('a')
        y = ord(s[i+1]) - ord('0')
        if i+2 < len(s) and s[i+2].isdigit():
            y = y * 10 + ord(s[i+2]) - ord('0') - 1
            i += 3
        else:
            y = y - 1
            i += 2
        pos += [(x,y)]
    return pos

def psq_to_psq(_psq, board_size):
    psq = ''
    #psq += 'Piskvorky ' + str(board_size) + "x" + str(board_size) + "," + " 11:11," + " 0\n"
    for x,y,t in _psq:
        psq += str(x)+","+str(y)+","+str(t)+"\n"
    return psq
