int func(int x) {
    if (x > 0) {
        return 1;
        x = x + 1;  // dead code after return
    }
    return 0;
}