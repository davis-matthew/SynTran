#include <iostream>
    unsigned long long A115969(unsigned int n) {
    if (n == 0) return 1;
    unsigned long long a[n + 1];
    a[0] = 1;
    a[1] = 6;
    for (unsigned int i = 2; i <= n; ++i) {
        a[i] = (3 * i * a[i - 1] + 3 * (9 - 14 * i) * a[i - 2] + (151 * i - 225) * a[i - 3] + 12 * (9 - 4 * i) * a[i - 4] + 4 * (i - 3) * a[i - 5]) / (3 * n);
    }
    return a[n];
}

        int main() {
            for(int i = 0 ; i <22; i++){
                A115969(i);
            }
        }
        