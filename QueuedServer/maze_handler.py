from random import randint as rand
import json

def generate_maze_visible(rows, cols):
    '''
    Returns: a tuple containing the generated maze and the visibility matrix.
    '''
    maze = generate_maze(rows + 2, cols + 2)
    maze = [i[1:-1] for i in maze[1:-1]]
    visible = [[False] * len(maze[0]) for i in range(len(maze))]
    visible[0][0] = True
    return (maze, visible)

def matrix_to_JSON(matrix):
    serialized = []
    for row in range(0, len(matrix)):
        for col in range(0, len(matrix[0])):
            serialized.append({'row': row,
                               'col': col,
                               'content': matrix[row][col]})
    return json.dumps(serialized)

def validate_mov(current_row, current_col, next_row, next_col, maze_vis):
    '''
    Returns: True if the next move (next_row and next_col) is valid.
    '''
    row_size = len(maze_vis[0])
    col_size = len(maze_vis[0][0])

    # Check boundaries
    if next_row < 0 or next_row >= row_size:
        return False
    if next_col < 0 or next_col >= col_size:
        return False

    # Check that the next position is adjacent to the current position
    row_diff = next_row - current_row
    col_diff = next_col - current_col
    if row_diff not in (-1, 0, 1):
        return False
    if col_diff not in (-1, 0, 1):
        return False

    # Check that the next position square is visible:
    if not maze_vis[1][next_row][next_col]:
        return False

    # Check that the next position square is not a wall:
    if maze_vis[0][next_row][next_col]:
        return False

    return True


def validate_unlock(target_row, target_col, maze_vis, pos_row, pos_col, maze):
    '''
    Returns: True if the target square (target_row, target_col) is unlockable.
    '''
    row_size = len(maze_vis[0])
    col_size = len(maze_vis[0][0])
    
    if(check_win(target_row, target_col, maze_vis)):
        return 2

    # Check boundaries
    if target_row < 0 or target_row >= row_size:
        return False
    if target_row < 0 or target_row >= col_size:
        return False

    # Check adjacent visible squares
    if target_row - 1 >= 0:
        if target_col - 1 >= 0 and maze_vis[1][target_row - 1][target_col - 1] and not maze[target_row - 1][target_col - 1]:
            return True
        if maze_vis[1][target_row - 1][target_col] and not maze[target_row - 1][target_col]:
            return True
        if (target_col + 1 < row_size and
                maze_vis[1][target_row - 1][target_col + 1] and not maze[target_row - 1][target_col + 1]):
            
            return True
    if target_col - 1 >= 0 and maze_vis[1][target_row][target_col - 1] and not maze[target_row][target_col - 1]:
        return True
    if target_col + 1 < row_size and maze_vis[1][target_row][target_col + 1] and not maze[target_row][target_col + 1]:
        return True
    if target_row + 1 < row_size:
        if target_col - 1 >= 0 and maze_vis[1][target_row + 1][target_col - 1] and not maze[target_row + 1][target_col - 1]:
            return True
        if maze_vis[1][target_row + 1][target_col] and not maze[target_row + 1][target_col]:
            return True
        if (target_col + 1 < row_size and
                maze_vis[1][target_row + 1][target_col + 1] and not maze[target_row + 1][target_col + 1]):
            return True

    return False

def validate_unlock_pos(target_row, target_col, maze_vis, pos_row, pos_col, maze):
    '''
    Returns: True if the target square (target_row, target_col) is unlockable.
    '''
    row_size = len(maze_vis[0])
    col_size = len(maze_vis[0][0])
    
    # Check closeness with the actual position pos_row, pos_col
    if(abs(pos_row-target_row)>1 or abs(pos_col-target_col)>1):
        return False

    if(check_win(target_row, target_col, maze_vis)):
        return 2

    # Check boundaries
    if target_row < 0 or target_row >= row_size:
        return False
    if target_row < 0 or target_row >= col_size:
        return False

    # Check adjacent visible squares
    if target_row - 1 >= 0:
        if target_col - 1 >= 0 and maze_vis[1][target_row - 1][target_col - 1] and not maze[target_row - 1][target_col - 1]:
            return True
        if maze_vis[1][target_row - 1][target_col] and not maze[target_row - 1][target_col]:
            return True
        if (target_col + 1 < row_size and
                maze_vis[1][target_row - 1][target_col + 1] and not maze[target_row - 1][target_col + 1]):
            
            return True
    if target_col - 1 >= 0 and maze_vis[1][target_row][target_col - 1] and not maze[target_row][target_col - 1]:
        return True
    if target_col + 1 < row_size and maze_vis[1][target_row][target_col + 1] and not maze[target_row][target_col + 1]:

        return True
    if target_row + 1 < row_size:
        if target_col - 1 >= 0 and maze_vis[1][target_row + 1][target_col - 1] and not maze[target_row + 1][target_col - 1]:
            return True
        if maze_vis[1][target_row + 1][target_col] and not maze[target_row + 1][target_col]:
            return True
        if (target_col + 1 < row_size and
                maze_vis[1][target_row + 1][target_col + 1] and not maze[target_row + 1][target_col + 1]):
            return True

    return False


def check_win(pos_row, pos_col, maze_vis):
    '''
    Returns: True if the player win in the position (pos_row, pos_col).
    '''
    row_size = len(maze_vis[0])
    col_size = len(maze_vis[0][0])

    # Check that the position is the same as the goal position
    if pos_row == row_size - 1 and pos_col == col_size - 1:
        return True

    return False

def generate_maze(width=81, height=51, complexity=.75, density=.75):
    # Only odd shapes
    shape = ((height // 2) * 2 + 1, (width // 2) * 2 + 1)
    # Adjust complexity and density relative to maze size
    complexity = int(complexity * (5 * (shape[0] + shape[1])))
    density = int(density * ((shape[0] // 2) * (shape[1] // 2)))
    # Build actual maze
    Z = [[False] * shape[1] for i in range(shape[0])]
    # Fill borders
    Z[0] = Z[-1] = [True] * shape[1]
    for i in range(len(Z)):
        Z[i][0] = True
        Z[i][-1] = True
    # Make aisles
    for i in range(density):
        x, y = rand(0, shape[1] // 2) * 2, rand(0, shape[0] // 2) * 2
        Z[y][x] = True
        for j in range(complexity):
            neighbours = []
            if x > 1:             neighbours.append((y, x - 2))
            if x < shape[1] - 2:  neighbours.append((y, x + 2))
            if y > 1:             neighbours.append((y - 2, x))
            if y < shape[0] - 2:  neighbours.append((y + 2, x))
            if len(neighbours):
                y_, x_ = neighbours[rand(0, len(neighbours) - 1)]
                if Z[y_][x_] == False:
                    Z[y_][x_] = True
                    Z[y_ + (y - y_) // 2][x_ + (x - x_) // 2] = True
                    x, y = x_, y_
    return Z
