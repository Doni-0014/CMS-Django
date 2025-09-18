    # def all_id(self):
    #     ids = []
    #     try:
    #         cursor = self.conn.cursor(pymysql.cursors.DictCursor)  
    #         cursor.execute(self.ALL_ID)  
    #         rows = cursor.fetchall()
    #         for row in rows:
    #             ids.append(row['staff_id']) 
    #     except Exception as e:
    #         print("Error fetching staff IDs: ", e)
    #     finally:
    #         cursor.close()
    
    #     return ids

    # def last_id(self):
    #     ids = self.all_id()
    #     if not ids:
    #         return "EMP1000"
    #     numeric_ids = [int(i[3:]) for i in ids if i.startswith("EMP")]
    #     max_id = max(numeric_ids)
    #     return f"EMP{max_id:04d}"
    
    # def incre_id(self):
    #     ids = self.all_id()
    #     if not ids:
    #         return "EMP1000"

    #     numeric_ids = [int(i[3:]) for i in ids if i.startswith("EMP")]
    #     max_id = max(numeric_ids)
    #     new_id = max_id + 1

    #     return f"EMP{new_id:04d}"