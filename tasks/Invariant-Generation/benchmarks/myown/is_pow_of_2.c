int is_power_of_two(int n) {
    return (n & (n-1)) == 0;
}