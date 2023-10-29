# from convert_utilites import calculate_elapsed_time, hms_str_to_timedelta, timedelta_to_hms_str
# from send_data_from_script_to_django_app import send_data_to_django
# from tasks_utilites import update_task_in_notion, clear_priority_in_notion
# from datetime import datetime
# from SQliteDB_class import SQLiteDB
# import os
#
#
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, 'time_tracking.db')
#
# in_progress_tasks = set()
# paused_tasks = set()
#
# def update_or_insert_task(task_id, task_name, status):
#     """Insert or update a task in the SQLite database."""
#     with SQLiteDB(DB_PATH) as db:
#         existing_task = db.fetch_one("SELECT status FROM tracking WHERE task_id=?", (task_id,))
#         now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#
#         previous_status = existing_task[0] if existing_task else None
#
#         # If the status hasn't changed, there's no need to update the elapsed time
#         if status == previous_status:
#             return
#
#         if status == "In progress" and task_id not in in_progress_tasks:
#             start_time = now
#             if existing_task:
#                 db.execute("UPDATE tracking SET status=?, start_time=?, task_name=? WHERE task_id=?",
#                                  (status, start_time, task_name, task_id))
#             else:
#                 db.execute("INSERT INTO tracking (task_id, task_name, status, start_time) VALUES (?, ?, ?, ?)",
#                                  (task_id, task_name, status, start_time))
#             update_task_in_notion(task_id, "Start time", start_time, value_type="date")
#             in_progress_tasks.add(task_id)
#             if task_id in paused_tasks:
#                 paused_tasks.remove(task_id)
#
#         elif status == "Paused" and task_id not in paused_tasks:
#             result = db.fetch_one("SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
#             start_time_str, previous_elapsed_time_str = result if result else (None, None)
#             if start_time_str:
#                 current_elapsed_time = calculate_elapsed_time(start_time_str, now)
#                 if previous_elapsed_time_str:
#                     previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
#                     total_elapsed_time = previous_elapsed_time + current_elapsed_time
#                 else:
#                     total_elapsed_time = current_elapsed_time
#                 elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
#                 db.execute("UPDATE tracking SET status=?, paused_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
#                                  (status, now, elapsed_time_str, task_name, task_id))
#                 update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
#                 update_task_in_notion(task_id, "Paused time", now, value_type="date")
#                 if task_id in in_progress_tasks:
#                     in_progress_tasks.remove(task_id)
#                 paused_tasks.add(task_id)
#
#         elif status == "Done":
#             if task_id in in_progress_tasks:
#                 start_time_str, previous_elapsed_time_str = db.fetch_one(
#                     "SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
#                 current_elapsed_time = calculate_elapsed_time(start_time_str, now)
#                 if previous_elapsed_time_str:
#                     previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
#                     total_elapsed_time = previous_elapsed_time + current_elapsed_time
#                 else:
#                     total_elapsed_time = current_elapsed_time
#                 elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
#                 db.execute("UPDATE tracking SET status=?, done_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
#                                  (status, now, elapsed_time_str, task_name, task_id))
#                 update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
#                 update_task_in_notion(task_id, "Done time", now, value_type="date")
#                 in_progress_tasks.remove(task_id)
#                 clear_priority_in_notion(task_id)
#
#             elif task_id in paused_tasks:
#                 paused_time = db.fetch_one("SELECT paused_time FROM tracking WHERE task_id=?", (task_id,))[0]
#                 db.execute("UPDATE tracking SET status=?, done_time=?, task_name=? WHERE task_id=?",
#                                  (status, paused_time, task_name, task_id))
#                 update_task_in_notion(task_id, "Done time", paused_time, value_type="date")
#                 paused_tasks.remove(task_id)
#                 clear_priority_in_notion(task_id)
#
#         else:
#             if existing_task:
#                 db.execute("UPDATE tracking SET status=?, task_name=? WHERE task_id=?",
#                                  (status, task_name, task_id))
#             else:
#                 db.execute("INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
#                                  (task_id, task_name, status))
#
#         send_data_to_django()
#
# # def handle_in_progress_status(task_id, task_name, status, db, now,in_progress_tasks, paused_tasks):
# #     existing_task = db.fetch_one("SELECT status FROM tracking WHERE task_id=?", (task_id,))
# #     now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# #     if status == "In progress" and task_id not in in_progress_tasks:
# #         start_time = now
# #         if existing_task:
# #             db.execute("UPDATE tracking SET status=?, start_time=?, task_name=? WHERE task_id=?",
# #                        (status, start_time, task_name, task_id))
# #         else:
# #             db.execute("INSERT INTO tracking (task_id, task_name, status, start_time) VALUES (?, ?, ?, ?)",
# #                        (task_id, task_name, status, start_time))
# #         update_task_in_notion(task_id, "Start time", start_time, value_type="date")
# #         in_progress_tasks.add(task_id)
# #         if task_id in paused_tasks:
# #             paused_tasks.remove(task_id)
# #
# #         send_data_to_django()
# #
# #
# # def handle_paused_status(task_id, task_name, status, db, now, in_progress_tasks, paused_tasks):
# #     if status == "Paused" and task_id not in paused_tasks:
# #         result = db.fetch_one("SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
# #         start_time_str, previous_elapsed_time_str = result if result else (None, None)
# #         if start_time_str:
# #             current_elapsed_time = calculate_elapsed_time(start_time_str, now)
# #             if previous_elapsed_time_str:
# #                 previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
# #                 total_elapsed_time = previous_elapsed_time + current_elapsed_time
# #             else:
# #                 total_elapsed_time = current_elapsed_time
# #             elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
# #             db.execute("UPDATE tracking SET status=?, paused_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
# #                        (status, now, elapsed_time_str, task_name, task_id))
# #             update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
# #             update_task_in_notion(task_id, "Paused time", now, value_type="date")
# #             if task_id in in_progress_tasks:
# #                 in_progress_tasks.remove(task_id)
# #             paused_tasks.add(task_id)
# #
# #         # send_data_to_django()
# #
# #
# # def handle_done_status(task_id, task_name, status, db, now, in_progress_tasks, paused_tasks):
# #     existing_task = db.fetch_one("SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
# #     if status == "Done":
# #         if task_id in in_progress_tasks:
# #             start_time_str, previous_elapsed_time_str = db.fetch_one(
# #                 "SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
# #             current_elapsed_time = calculate_elapsed_time(start_time_str, now)
# #             if previous_elapsed_time_str:
# #                 previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
# #                 total_elapsed_time = previous_elapsed_time + current_elapsed_time
# #             else:
# #                 total_elapsed_time = current_elapsed_time
# #             elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
# #             db.execute("UPDATE tracking SET status=?, done_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
# #                        (status, now, elapsed_time_str, task_name, task_id))
# #             update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
# #             update_task_in_notion(task_id, "Done time", now, value_type="date")
# #             in_progress_tasks.remove(task_id)
# #             clear_priority_in_notion(task_id)
# #
# #         elif task_id in paused_tasks:
# #             paused_time = db.fetch_one("SELECT paused_time FROM tracking WHERE task_id=?", (task_id,))[0]
# #             db.execute("UPDATE tracking SET status=?, done_time=?, task_name=? WHERE task_id=?",
# #                        (status, paused_time, task_name, task_id))
# #             update_task_in_notion(task_id, "Done time", paused_time, value_type="date")
# #             paused_tasks.remove(task_id)
# #             clear_priority_in_notion(task_id)
# #
# #     else:
# #         if existing_task:
# #             db.execute("UPDATE tracking SET status=?, task_name=? WHERE task_id=?",
# #                        (status, task_name, task_id))
# #         else:
# #             db.execute("INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
# #                        (task_id, task_name, status))
# #
# #     # send_data_to_django()
