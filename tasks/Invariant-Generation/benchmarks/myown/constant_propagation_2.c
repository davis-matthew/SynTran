int func(int x) {
    int a = 5 * 7;    // constant-folded to 35
    return a + x;
}