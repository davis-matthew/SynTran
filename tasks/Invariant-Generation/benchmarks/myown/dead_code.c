int func(int x) {
    int y = x * 2;
    if (0) {
        y = x + 10;  // dead code, never executed
    }
    return y;
}