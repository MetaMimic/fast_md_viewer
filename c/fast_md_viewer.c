#include <SDL.h>
#include <SDL_ttf.h>
#include <cmark.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_WINDOW_WIDTH 800
#define INITIAL_WINDOW_HEIGHT 600
#define FONT_SIZE 16
#define LINE_HEIGHT (FONT_SIZE + 4)
float zoom = 1.0f; // Global zoom factor

// Helper for word wrapping
#include <locale.h>
#include <wchar.h>

static int word_wrap_text(TTF_Font *font, const char *text, int font_size, int max_width, char ***lines_out) {
    // Returns number of wrapped lines, lines_out is malloc'd array of malloc'd strings
    int count = 0, cap = 8;
    char **lines = malloc(cap * sizeof(char*));
    if (!lines) return 0;
    char *buf = strdup(text);
    char *start = buf;
    while (*start) {
        // Find how much fits
        int len = 0, last_space = -1;
        for (int i = 0; start[i]; ++i) {
            if (start[i] == ' ') last_space = i;
            char save = start[i+1];
            start[i+1] = 0;
            int w = 0, h = 0;
            TTF_SetFontSize(font, font_size);
            TTF_SizeText(font, start, &w, &h);
            start[i+1] = save;
            if (w > max_width) {
                if (last_space >= 0) len = last_space + 1;
                else len = i;
                break;
            }
            len = i+1;
            if (!start[i+1]) break;
        }
        if (len == 0) break;
        char *line = malloc(len+1);
        strncpy(line, start, len);
        line[len] = 0;
        if (count == cap) {
            cap *= 2;
            lines = realloc(lines, cap * sizeof(char*));
        }
        lines[count++] = line;
        start += len;
        while (*start == ' ') start++; // skip spaces
    }
    free(buf);
    *lines_out = lines;
    return count;
}

// Helper to count list nesting level for indentation
static int get_list_level(cmark_node *node) {
    int level = 0;
    cmark_node *n = node;
    while (n) {
        if (cmark_node_get_type(n) == CMARK_NODE_LIST)
            level++;
        n = cmark_node_parent(n);
    }
    return level;
}

typedef struct {
    char *text;
    int font_size;
    SDL_Color color;
    int bold;
    int indent;
    int monospace;
    int is_list_item;
    int is_hr;
    int is_quote;
} TextLine;

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <markdown_file>\n", argv[0]);
        return 1;
    }

    // Initialize SDL2 and TTF
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        fprintf(stderr, "Error: SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    if (TTF_Init() < 0) {
        fprintf(stderr, "Error: TTF_Init failed: %s\n", TTF_GetError());
        SDL_Quit();
        return 1;
    }

    // Create resizable window
    SDL_Window *window = SDL_CreateWindow("Fast MD Viewer", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                          INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT,
                                          SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (!window) {
        fprintf(stderr, "Error: SDL_CreateWindow failed: %s\n", SDL_GetError());
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    SDL_Renderer *renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer) {
        fprintf(stderr, "Error: SDL_CreateRenderer failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    // Get initial window size
    int window_width = INITIAL_WINDOW_WIDTH;
    int window_height = INITIAL_WINDOW_HEIGHT;
    SDL_GetWindowSize(window, &window_width, &window_height);
    printf("Initial window size: %dx%d\n", window_width, window_height);

    // Load font
    TTF_Font *font = TTF_OpenFont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE);
    if (!font) {
        fprintf(stderr, "Error: Could not load font: %s\n", TTF_GetError());
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    // Read Markdown file
    FILE *file = fopen(argv[1], "r");
    if (!file) {
        fprintf(stderr, "Error: Could not open file: %s\n", argv[1]);
        TTF_CloseFont(font);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);
    char *md_text = malloc(size + 1);
    if (!md_text) {
        fclose(file);
        TTF_CloseFont(font);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }
    size_t read_size = fread(md_text, 1, size, file);
    md_text[read_size] = '\0';
    fclose(file);

    // Parse Markdown with cmark
    cmark_node *doc = cmark_parse_document(md_text, read_size, CMARK_OPT_DEFAULT);
    free(md_text);
    if (!doc) {
        fprintf(stderr, "Error: Failed to parse Markdown\n");
        TTF_CloseFont(font);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    // Convert to text lines with block structure
    TextLine lines[10000];
    int line_count = 0;
    cmark_iter *iter = cmark_iter_new(doc);
    cmark_event_type ev_type;

    while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE && line_count < 10000) {
        cmark_node *node = cmark_iter_get_node(iter);
        cmark_node_type type = cmark_node_get_type(node);

        if (ev_type == CMARK_EVENT_ENTER) {
            if (type == CMARK_NODE_TEXT) {
                const char *text = cmark_node_get_literal(node);
                if (text && strlen(text) > 0) {
                    lines[line_count].text = strdup(text);
                    lines[line_count].font_size = FONT_SIZE;
                    lines[line_count].color = (SDL_Color){0, 0, 0, 255}; // Black text
                    lines[line_count].bold = 0;
                    lines[line_count].indent = 0;
                    lines[line_count].monospace = 0;
                    lines[line_count].is_list_item = 0;
                    lines[line_count].is_hr = 0;
                    lines[line_count].is_quote = 0;

                    cmark_node *parent = cmark_node_parent(node);
                    if (parent) {
                        cmark_node_type parent_type = cmark_node_get_type(parent);
                        if (parent_type == CMARK_NODE_HEADING) {
                            lines[line_count].font_size = FONT_SIZE + 4 * (7 - cmark_node_get_heading_level(parent));
                            lines[line_count].bold = 1;
                        } else if (parent_type == CMARK_NODE_STRONG) {
                            lines[line_count].bold = 1;
                        } else if (parent_type == CMARK_NODE_LIST) {
                            lines[line_count].indent = 2 * get_list_level(parent);
                        } else if (parent_type == CMARK_NODE_ITEM) {
                            lines[line_count].is_list_item = 1;
                            cmark_node *list = cmark_node_parent(parent);
                            if (list && cmark_node_get_type(list) == CMARK_NODE_LIST) {
                                lines[line_count].indent = 2 * get_list_level(list);
                            }
                        } else if (parent_type == CMARK_NODE_CODE_BLOCK) {
                            lines[line_count].monospace = 1;
                        } else if (parent_type == CMARK_NODE_BLOCK_QUOTE) {
                            lines[line_count].is_quote = 1;
                            lines[line_count].indent += 2;
                        }
                    }
                    printf("Parsed line %d: %s (bold: %d, size: %d, indent: %d, mono: %d, list: %d, hr: %d, quote: %d)\n",
                        line_count, lines[line_count].text,
                        lines[line_count].bold, lines[line_count].font_size,
                        lines[line_count].indent, lines[line_count].monospace,
                        lines[line_count].is_list_item, lines[line_count].is_hr, lines[line_count].is_quote);
                    line_count++;
                }
            } else if (type == CMARK_NODE_PARAGRAPH || type == CMARK_NODE_ITEM || type == CMARK_NODE_LIST) {
                if (line_count > 0 && line_count < 10000) {
                    lines[line_count].text = strdup("");
                    lines[line_count].font_size = FONT_SIZE;
                    lines[line_count].color = (SDL_Color){0, 0, 0, 255};
                    lines[line_count].bold = 0;
                    lines[line_count].indent = 0;
                    lines[line_count].monospace = 0;
                    lines[line_count].is_list_item = 0;
                    lines[line_count].is_hr = 0;
                    lines[line_count].is_quote = 0;
                    printf("Parsed line %d: (blank)\n", line_count);
                    line_count++;
                }
            } else if (type == CMARK_NODE_CODE_BLOCK) {
                if (line_count < 10000) {
                    const char *code = cmark_node_get_literal(node);
                    if (code) {
                        lines[line_count].text = strdup(code);
                        lines[line_count].font_size = FONT_SIZE;
                        lines[line_count].color = (SDL_Color){0, 0, 0, 255};
                        lines[line_count].bold = 0;
                        lines[line_count].indent = 2;
                        lines[line_count].monospace = 1;
                        lines[line_count].is_list_item = 0;
                        lines[line_count].is_hr = 0;
                        lines[line_count].is_quote = 0;
                        line_count++;
                    }
                }
            } else if (type == CMARK_NODE_BLOCK_QUOTE) {
                if (line_count < 10000) {
                    lines[line_count].text = strdup("");
                    lines[line_count].font_size = FONT_SIZE;
                    lines[line_count].color = (SDL_Color){0, 0, 0, 255};
                    lines[line_count].bold = 0;
                    lines[line_count].indent = 2;
                    lines[line_count].monospace = 0;
                    lines[line_count].is_list_item = 0;
                    lines[line_count].is_hr = 0;
                    lines[line_count].is_quote = 1;
                    line_count++;
                }
            } else if (type == CMARK_NODE_THEMATIC_BREAK) {
                if (line_count < 10000) {
                    lines[line_count].text = strdup("---");
                    lines[line_count].font_size = FONT_SIZE;
                    lines[line_count].color = (SDL_Color){0, 0, 0, 255};
                    lines[line_count].bold = 0;
                    lines[line_count].indent = 0;
                    lines[line_count].monospace = 0;
                    lines[line_count].is_list_item = 0;
                    lines[line_count].is_hr = 1;
                    lines[line_count].is_quote = 0;
                    line_count++;
                }
            }
        }
    }
    cmark_iter_free(iter);
    cmark_node_free(doc);

    if (line_count == 0) {
        fprintf(stderr, "Warning: No lines parsed from file\n");
        lines[line_count].text = strdup("No content to display");
        lines[line_count].font_size = FONT_SIZE;
        lines[line_count].color = (SDL_Color){0, 0, 0, 255};
        lines[line_count].bold = 0;
        line_count = 1;
    }

    // Scrolling and rendering state
    int offset_y = 0;
    int max_offset = line_count * LINE_HEIGHT - window_height;
    if (max_offset < 0) max_offset = 0;

    // Main loop
    SDL_Event event;
    int running = 1;
    while (running) {
        if (SDL_WaitEvent(&event)) {
            int redraw = 0;
            switch (event.type) {
                case SDL_QUIT:
                    running = 0;
                    break;
                case SDL_MOUSEWHEEL:
                    if (SDL_GetModState() & KMOD_CTRL) {
                        // Zoom in/out in 5% steps
                        if (event.wheel.y > 0) {
                            zoom += 0.05f;
                            if (zoom > 3.0f) zoom = 3.0f;
                        } else if (event.wheel.y < 0) {
                            zoom -= 0.05f;
                            if (zoom < 0.5f) zoom = 0.5f;
                        }
                        redraw = 1;
                    } else {
                        offset_y -= event.wheel.y * (int)(30 * zoom);
                        if (offset_y < 0) offset_y = 0;
                        if (offset_y > max_offset) offset_y = max_offset;
                        redraw = 1;
                    }
                    break;
                case SDL_WINDOWEVENT:
                    if (event.window.event == SDL_WINDOWEVENT_SIZE_CHANGED ||
                        event.window.event == SDL_WINDOWEVENT_EXPOSED) {
                        SDL_GetWindowSize(window, &window_width, &window_height);
                        max_offset = (int)(line_count * LINE_HEIGHT * zoom) - window_height;
                        if (max_offset < 0) max_offset = 0;
                        if (offset_y > max_offset) offset_y = max_offset;
                        redraw = 1;
                    }
                    break;
                default:
                    redraw = 1;
                    break;
            }
            if (!running) break;
            if (!redraw) continue;
        } else {
            continue;
        }

        // Always render for immediate display
        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255); // White background
        SDL_RenderClear(renderer);

        int visible_lines = (int)(window_height / (LINE_HEIGHT * zoom)) + 1;
        int start_line = (int)(offset_y / (LINE_HEIGHT * zoom));
        int end_line = start_line + visible_lines;
        if (end_line > line_count) end_line = line_count;

        printf("Rendering lines %d to %d (offset_y: %d, window_height: %d)\n",
               start_line, end_line, offset_y, window_height);

        int y = 0;
        for (int i = start_line; i < end_line; i++) {
            if (!lines[i].text) continue;
            int font_size = (int)(lines[i].font_size * zoom);
            int x = 10 + lines[i].indent * 20;
            // Render horizontal rule
            if (lines[i].is_hr) {
                SDL_SetRenderDrawColor(renderer, 180, 180, 180, 255);
                SDL_RenderDrawLine(renderer, 10, y + font_size / 2, window_width - 10, y + font_size / 2);
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
                y += (int)(LINE_HEIGHT * zoom);
                continue;
            }
            // Render blockquote background
            if (lines[i].is_quote) {
                SDL_Rect quote_rect = {x - 10, y, window_width - x, font_size + 4};
                SDL_SetRenderDrawColor(renderer, 230, 230, 255, 255);
                SDL_RenderFillRect(renderer, &quote_rect);
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
            }
            // Render code block background
            if (lines[i].monospace) {
                SDL_Rect code_rect = {x - 5, y, window_width - x, font_size + 4};
                SDL_SetRenderDrawColor(renderer, 240, 240, 240, 255);
                SDL_RenderFillRect(renderer, &code_rect);
                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
            }
            // Set font style
            TTF_SetFontStyle(font, lines[i].bold ? TTF_STYLE_BOLD : TTF_STYLE_NORMAL);
            TTF_SetFontSize(font, font_size);
            // Render bullet for list items
            char *render_text = lines[i].text;
            char bullet[4] = "\u2022 ";
            if (lines[i].is_list_item) {
                render_text = malloc(strlen(lines[i].text) + 8);
                strcpy(render_text, bullet);
                strcat(render_text, lines[i].text);
            }
            // Word wrap
            char **wrapped = NULL;
            int wrap_count = word_wrap_text(font, render_text, font_size, window_width - x - 10, &wrapped);
            for (int w = 0; w < wrap_count; ++w) {
                SDL_Surface *surface = TTF_RenderUTF8_Blended(font, wrapped[w], lines[i].color);
                if (!surface) {
                    fprintf(stderr, "Error rendering text at line %d: %s\n", i, TTF_GetError());
                    continue;
                }
                SDL_Texture *texture = SDL_CreateTextureFromSurface(renderer, surface);
                if (!texture) {
                    fprintf(stderr, "Error creating texture at line %d: %s\n", i, SDL_GetError());
                    SDL_FreeSurface(surface);
                    continue;
                }
                int tw, th;
                TTF_SizeText(font, wrapped[w], &tw, &th);
                SDL_Rect dst = {x, y, tw < window_width - x - 10 ? tw : window_width - x - 10, th};
                SDL_RenderCopy(renderer, texture, NULL, &dst);
                SDL_DestroyTexture(texture);
                SDL_FreeSurface(surface);
                y += (int)(LINE_HEIGHT * zoom);
            }
            for (int w = 0; w < wrap_count; ++w) free(wrapped[w]);
            free(wrapped);
            if (lines[i].is_list_item && render_text != lines[i].text) free(render_text);
        }

        SDL_RenderPresent(renderer);
    }

    // Cleanup
    for (int i = 0; i < line_count; i++) {
        if (lines[i].text) free(lines[i].text);
    }
    TTF_CloseFont(font);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();
    return 0;
}
