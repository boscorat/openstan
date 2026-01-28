CREATE TRIGGER new_statement_queue
AFTER INSERT on statement_queue
BEGIN
	INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
	VALUES 	(NEW.session_id
				, CURRENT_TIMESTAMP 					
				, "statement_queue" 									
				, "INSERT" 								
				, NEW.queue_id						
				, 1 												
				, concat("Item added to Statement Queue: ", NEW.path) 	
				);
END