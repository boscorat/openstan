drop TRIGGER IF EXISTS new_session;

CREATE TRIGGER new_session
AFTER INSERT on session
BEGIN
	INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
	VALUES 	(NEW.session_id
				, CURRENT_TIMESTAMP 					
				, "session" 									
				, "INSERT" 								
				, NEW.session_id						
				, 1 												
				, concat("Session created") 	
				);
END;
