import json, re
def tight(s):
    s = str(s).lower()
    s = re.sub(r'\\[a-zA-Z]+', '', s)   # 去掉 \frac \sqrt 等命令名
    s = re.sub(r'[\s{}\[\],;$]', '', s)
    s = re.sub(r'[^\w\.\-/+=]', '', s)
    return s
if __name__ == '__main__':
    tests = [('y _ { 2 } = - 1', 'y _ { 2 } = - 1\n'),
             ('\\[x_{1}= \\frac{-2+2 \\sqrt{2}}{2}\\]', 'x _ { 1 } = \\frac { - 2 + 2 \\sqrt { 2 } } { 2 }\n')]
    for a,b in tests:
        print('equal:', tight(a) == tight(b), '|', tight(a)[:40])
