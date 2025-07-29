int func(int x) {
    int a = 5;
    int b = a + 3;    // compiler can replace b by 8
    return b * x;
}