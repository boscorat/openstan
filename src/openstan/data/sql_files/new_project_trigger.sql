drop TRIGGER IF EXISTS new_project;

CREATE TRIGGER new_project
AFTER INSERT on project
BEGIN
	INSERT INTO event_log (session_id, log_time, table_name, update_action, record_id, success, message)
	VALUES 	(NEW.createdBy_session
				, CURRENT_TIMESTAMP 					
				, "project" 									
				, "INSERT" 								
				, NEW.project_id						
				, 1 												
				, concat("Project created: ", NEW.project_name) 	
				);
END;
