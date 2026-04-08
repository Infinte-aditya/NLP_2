import json
import pdfplumber  

with pdfplumber.open('j1930_200204.pdf') as pdf:
        
        for p in range(6,27):
            page = pdf.pages[p]

            v_lines = [63,225,387,549]

            h_lines = [124 + (i*12) for i in range(50)]
            if 722 not in h_lines:
                   h_lines.append(722)

            settings = {
                "vertical_strategy": "explicit",
                "horizontal_strategy": "explicit",
                "explicit_vertical_lines": v_lines,
                "explicit_horizontal_lines": h_lines,
            }

            table = page.extract_table(table_settings=settings)
            with open ("new_glossary.jsonl", "a") as file:

                n = len(table)
                print(n)
                print(table[0])
                print(table[0][0],table[0][1],table[0][2])
                  
                for i in range(n):          
                    entry = {
                        "term": [
                                f"{table[i][0]}",
                                f"{table[i][1]}",
                                f"{table[i][2]}",
                                
                        ]
                    }

                    file.write(json.dumps(entry) + "\n")
                  
                        
                # if table:
                #     for row in table:
                #         print(row)


            # im = first_page.to_image(resolution=300)
            # line_x0 = [(63,124),(549,124)]
            # line_x1 = [(63,722),(549,722)]
            # line_y1 = [(225,124),(225,722)]
            # line_y2 = [(387,124),(387,722)]
            # line_y0 = [(63,124),(63,722)]
            # line_y4 = [(549,124),(549,722)]
            # im.draw_line(line_x0, stroke=(255,0,0,255), stroke_width=2)
            # im.draw_line(line_y1, stroke=(255,0,0,255), stroke_width=2)
            # im.draw_line(line_y2, stroke=(255,0,0,255), stroke_width=2)
            # im.draw_line(line_y0, stroke=(255,0,0,255), stroke_width=2)
            # im.draw_line(line_y4, stroke=(255,0,0,255), stroke_width=2)
            # im.draw_line(line_x1, stroke=(255,0,0,255), stroke_width=2)
            # d= 12
            # s=124
            # for i in range(50):
            #         s = s+d
            #         line_loop = [(63,s),(549,s)]
            #         im.draw_line(line_loop, stroke=(255,0,0,255), stroke_width=2)

            # # im.debug_tablefinder()
            # im.show()


    
