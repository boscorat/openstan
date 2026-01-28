drop TRIGGER IF EXISTS new_user;

CREATE TRIGGER new_user
AFTER INSERT on user
BEGIN
	INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
	VALUES 	(NEW.createdBy_session
				, CURRENT_TIMESTAMP 					
				, "user" 									
				, "INSERT" 								
				, NEW.user_id						
				, 1 												
				, concat("User created: " ,NEW.username) 	
				);
END;