function pos = CenteredDialog(fh, width, height)
%CENTEREDDIALOG  - center a dialog on current figure
%
%	usage:  pos = CenteredDialog(fh, h, w)
%
% returns POS [x , y, width, height] needed to center
% a dialog of WIDTH and HEIGHT pixels on figure FH

% mkt 08/09

if nargin < 3,
	eval('help CenteredDialog');
	return;
end;

units = get(fh, 'units');
if strcmpi(units,'pixels'),
	units = [];
else,
	set(fh, 'units','pixels');
end;	
fPos = get(fh, 'position');
if ~isempty(units), set(fh, 'units',units); end;

pos = [fPos(1)+(fPos(3)-width)/2 , fPos(2)+(fPos(4)-height)/2 , width , height];
