int func(int n) {
    int c = 10;      // loop-invariant
    int sum = 0;
    for(int i = 0; i < n; i++) {
        sum += c;    // repeatedly adds 10
    }
    return sum;
}