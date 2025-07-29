int mod_sub(int x, int y) {
    while(x >= y) {
        x -= y;
    }
    return x;
}