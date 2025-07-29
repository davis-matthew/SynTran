int pair_count(int n) {
    int count = 0;
    for(int i = 0; i < n; i++) {
        for(int j = i+1; j < n; j++) {
            count++;
        }
    }
    return count;
}