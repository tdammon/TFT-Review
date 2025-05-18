-- Check if event_id column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='comment' AND column_name='event_id'
    ) THEN
        -- Add event_id column
        ALTER TABLE comment ADD COLUMN event_id UUID;
        
        -- Add foreign key constraint
        ALTER TABLE comment 
        ADD CONSTRAINT fk_comment_event_id 
        FOREIGN KEY (event_id) 
        REFERENCES event(id);
        
        RAISE NOTICE 'Added event_id column and foreign key to comment table';
    ELSE
        RAISE NOTICE 'event_id column already exists in comment table';
    END IF;
END $$; 