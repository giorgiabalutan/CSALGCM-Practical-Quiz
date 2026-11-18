def Levenshtein(w1, w2) -> int:
    m = len(w1) + 1
    n = len(w2) + 1

    G = [[0] * n for i in range(m)]

    for i in range(m):
        G[i][0] = i

    for j in range(n):
        G[0][j] = j

    for i in range(1, m):
        for j in range(1, n):

            if w1[i-1] == w2[j-1]:
                extra = 0
            else:
                extra = 1

            G[i][j] = min(
                G[i-1][j] + 1,
                G[i][j-1] + 1,
                G[i-1][j-1] + extra
            )

            # For Damerau-Levenshtein (restricted)
            if i > 1 and j > 1 and w1[i-1] == w2[j-2] and w1[i-2] == w2[j-1]:
                G[i][j] = min(G[i][j], G[i-2][j-2] + 1)

    return G[m-1][n-1]
